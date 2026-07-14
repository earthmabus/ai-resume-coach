import json
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from core.health import live, ready


def _body(response):
    return json.loads(response["body"])


def test_liveness_returns_200_without_external_calls():
    with patch("core.health.boto3.client") as boto_client:
        response = live({})

    assert response["statusCode"] == 200
    assert _body(response)["status"] == "alive"
    assert _body(response)["check"] == "liveness"
    boto_client.assert_not_called()


def test_readiness_returns_200_when_dependencies_pass():
    dynamodb_client = MagicMock()
    sqs_client = MagicMock()

    def client_factory(service_name):
        if service_name == "dynamodb":
            return dynamodb_client
        if service_name == "sqs":
            return sqs_client
        raise AssertionError(f"Unexpected service: {service_name}")

    with patch("core.health.boto3.client", side_effect=client_factory):
        response = ready({})

    body = _body(response)

    assert response["statusCode"] == 200
    assert body["status"] == "ready"
    assert body["checks"]["configuration"]["status"] == "pass"
    assert body["checks"]["dynamodb"]["status"] == "pass"
    assert body["checks"]["sqs"]["status"] == "pass"

    dynamodb_client.describe_table.assert_called_once_with(
        TableName="test-table"
    )
    sqs_client.get_queue_attributes.assert_called_once()


def test_readiness_returns_503_when_dynamodb_fails():
    error = ClientError(
        {
            "Error": {
                "Code": "AccessDeniedException",
                "Message": "sensitive aws error",
            }
        },
        "DescribeTable",
    )

    dynamodb_client = MagicMock()
    dynamodb_client.describe_table.side_effect = error

    sqs_client = MagicMock()

    def client_factory(service_name):
        if service_name == "dynamodb":
            return dynamodb_client
        if service_name == "sqs":
            return sqs_client
        raise AssertionError(f"Unexpected service: {service_name}")

    with patch("core.health.boto3.client", side_effect=client_factory):
        response = ready({})

    body = _body(response)

    assert response["statusCode"] == 503
    assert body["status"] == "not-ready"
    assert body["checks"]["dynamodb"]["status"] == "fail"
    assert "sensitive aws error" not in response["body"]


def test_readiness_returns_503_when_sqs_fails():
    error = ClientError(
        {
            "Error": {
                "Code": "AccessDenied",
                "Message": "sensitive queue error",
            }
        },
        "GetQueueAttributes",
    )

    dynamodb_client = MagicMock()
    sqs_client = MagicMock()
    sqs_client.get_queue_attributes.side_effect = error

    def client_factory(service_name):
        if service_name == "dynamodb":
            return dynamodb_client
        if service_name == "sqs":
            return sqs_client
        raise AssertionError(f"Unexpected service: {service_name}")

    with patch("core.health.boto3.client", side_effect=client_factory):
        response = ready({})

    body = _body(response)

    assert response["statusCode"] == 503
    assert body["status"] == "not-ready"
    assert body["checks"]["sqs"]["status"] == "fail"
    assert "sensitive queue error" not in response["body"]
