import json
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from core.config import ConfigurationError
from core.health import (
    READINESS_CONNECT_TIMEOUT_SECONDS,
    READINESS_MAX_ATTEMPTS,
    READINESS_READ_TIMEOUT_SECONDS,
    live,
    ready,
)


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

    def client_factory(service_name, **kwargs):
        assert "config" in kwargs

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
    assert body["siteName"] == "east"
    assert body["regionRole"] == "active"
    assert body["currentRegion"] == "us-east-1"
    assert body["regionalHealth"]["scope"] == "readiness"
    assert body["regionalHealth"]["status"] == "HEALTHY"
    assert (
        body["regionalHealth"]["reasonCode"]
        == "ALL_REQUIRED_CHECKS_PASS"
    )
    assert body["regionalHealth"]["currentRegion"] == "us-east-1"
    assert body["regionalHealth"]["evaluatedAt"]
    assert {
        observation["name"]: observation
        for observation in body["observations"]
    }["dynamodb"]["fresh"] is True
    assert body["checks"]["configuration"]["status"] == "pass"
    assert body["checks"]["dynamodb"]["status"] == "pass"
    assert body["checks"]["sqs"]["status"] == "pass"
    assert "QueueUrl" not in response["body"]
    assert "TableName" not in response["body"]

    dynamodb_client.describe_table.assert_called_once_with(
        TableName="test-table"
    )
    sqs_client.get_queue_attributes.assert_called_once()


def test_readiness_uses_bounded_sdk_timeouts_and_attempts():
    dynamodb_client = MagicMock()
    sqs_client = MagicMock()

    def client_factory(service_name, **kwargs):
        client_config = kwargs["config"]

        assert client_config.connect_timeout == (
            READINESS_CONNECT_TIMEOUT_SECONDS
        )
        assert client_config.read_timeout == (
            READINESS_READ_TIMEOUT_SECONDS
        )
        assert (
            client_config.retries["max_attempts"]
            == READINESS_MAX_ATTEMPTS
        )

        if service_name == "dynamodb":
            return dynamodb_client
        if service_name == "sqs":
            return sqs_client
        raise AssertionError(f"Unexpected service: {service_name}")

    with patch("core.health.boto3.client", side_effect=client_factory):
        response = ready({})

    assert response["statusCode"] == 200


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

    def client_factory(service_name, **kwargs):
        assert "config" in kwargs

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
    assert body["regionalHealth"]["scope"] == "readiness"
    assert body["regionalHealth"]["status"] == "DEGRADED"
    assert (
        body["regionalHealth"]["reasonCode"]
        == "PARTIAL_DEPENDENCY_FAILURE"
    )
    assert body["checks"]["dynamodb"]["status"] == "fail"
    assert {
        observation["name"]: observation
        for observation in body["observations"]
    }["dynamodb"]["reasonCode"] == "DEPENDENCY_UNAVAILABLE"
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

    def client_factory(service_name, **kwargs):
        assert "config" in kwargs

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
    assert body["regionalHealth"]["scope"] == "readiness"
    assert body["regionalHealth"]["status"] == "DEGRADED"
    assert (
        body["regionalHealth"]["reasonCode"]
        == "PARTIAL_DEPENDENCY_FAILURE"
    )
    assert body["checks"]["sqs"]["status"] == "fail"
    assert "sensitive queue error" not in response["body"]


def test_readiness_reports_unavailable_when_runtime_dependencies_fail():
    dynamodb_error = ClientError(
        {
            "Error": {
                "Code": "AccessDeniedException",
                "Message": "sensitive dynamodb error",
            }
        },
        "DescribeTable",
    )
    sqs_error = ClientError(
        {
            "Error": {
                "Code": "AccessDenied",
                "Message": "sensitive queue error",
            }
        },
        "GetQueueAttributes",
    )

    dynamodb_client = MagicMock()
    dynamodb_client.describe_table.side_effect = dynamodb_error
    sqs_client = MagicMock()
    sqs_client.get_queue_attributes.side_effect = sqs_error

    def client_factory(service_name, **kwargs):
        assert "config" in kwargs

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
    assert body["regionalHealth"]["scope"] == "readiness"
    assert body["regionalHealth"]["status"] == "UNAVAILABLE"
    assert (
        body["regionalHealth"]["reasonCode"]
        == "DEPENDENCY_UNAVAILABLE"
    )
    assert body["checks"]["configuration"]["status"] == "pass"


def test_readiness_reports_unknown_when_configuration_fails():
    with patch(
        "core.health.get_config",
        side_effect=ConfigurationError("missing configuration"),
    ):
        response = ready({})

    body = _body(response)

    assert response["statusCode"] == 503
    assert body["status"] == "not-ready"
    assert body["regionalHealth"]["scope"] == "readiness"
    assert body["regionalHealth"]["status"] == "UNKNOWN"
    assert (
        body["regionalHealth"]["reasonCode"]
        == "CONFIGURATION_INVALID"
    )
    assert body["regionalHealth"]["evaluatedAt"]
    assert body["checks"]["configuration"]["status"] == "fail"
    assert body["observations"][0]["dimension"] == "configuration"
    assert body["observations"][0]["reasonCode"] == "CONFIGURATION_INVALID"
    assert "missing configuration" not in response["body"]
