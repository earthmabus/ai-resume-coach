from __future__ import annotations

import json
from unittest.mock import MagicMock

from botocore.exceptions import ClientError

from core.regional_transport import (
    DeliveryStatus,
    RegionalDeliveryRequest,
    SqsRegionalTransport,
)


def request(
    owner_region: str = "us-west-2",
) -> RegionalDeliveryRequest:
    return RegionalDeliveryRequest(
        current_region="us-east-1",
        owner_region=owner_region,
        payload={
            "schemaVersion": 1,
            "workId": "work-123",
        },
        request_id="request-123",
        delivery_type="processing_queue",
        correlation_id="correlation-123",
    )


def test_local_placement_performs_no_transport():
    client_factory = MagicMock()
    transport = SqsRegionalTransport(
        client_factory=client_factory,
        queue_names_by_region={
            "us-east-1": "east-processing",
        },
    )

    result = transport.deliver(
        request(owner_region="us-east-1")
    )

    assert result.status == DeliveryStatus.NOOP_LOCAL
    assert not result.delivered
    client_factory.assert_not_called()


def test_non_local_placement_sends_one_sqs_message():
    client = MagicMock()
    client.get_queue_url.return_value = {
        "QueueUrl": "https://sqs.us-west-2.example/queue",
    }
    client.send_message.return_value = {
        "MessageId": "message-123",
    }

    transport = SqsRegionalTransport(
        client_factory=MagicMock(return_value=client),
        queue_names_by_region={
            "us-west-2": "west-processing",
        },
    )

    result = transport.deliver(request())

    assert result.status == DeliveryStatus.DELIVERED
    assert result.delivered
    assert result.message_id == "message-123"
    assert result.as_dict()["deliveryMessageId"] == "message-123"
    assert result.as_dict()["transportMessageId"] == "message-123"
    client.get_queue_url.assert_called_once_with(
        QueueName="west-processing"
    )
    client.send_message.assert_called_once()

    message = json.loads(
        client.send_message.call_args.kwargs["MessageBody"]
    )

    assert message == {
        "schemaVersion": 1,
        "workId": "work-123",
    }


def test_queue_url_is_resolved_once_per_process_region():
    client = MagicMock()
    client.get_queue_url.return_value = {
        "QueueUrl": "https://sqs.us-west-2.example/queue",
    }
    client.send_message.return_value = {
        "MessageId": "message-123",
    }

    client_factory = MagicMock(return_value=client)
    transport = SqsRegionalTransport(
        client_factory=client_factory,
        queue_names_by_region={
            "us-west-2": "west-processing",
        },
    )

    first = transport.deliver(request())
    second = transport.deliver(request())

    assert first.status == DeliveryStatus.DELIVERED
    assert second.status == DeliveryStatus.DELIVERED
    client_factory.assert_called_once_with("us-west-2")
    client.get_queue_url.assert_called_once_with(
        QueueName="west-processing"
    )
    assert client.send_message.call_count == 2


def test_unsupported_region_reports_without_send():
    client_factory = MagicMock()
    transport = SqsRegionalTransport(
        client_factory=client_factory,
        queue_names_by_region={
            "us-east-1": "east-processing",
        },
    )

    result = transport.deliver(request())

    assert result.status == DeliveryStatus.UNSUPPORTED_REGION
    assert not result.delivered
    client_factory.assert_not_called()


def test_transport_failure_reports_failed_delivery():
    client = MagicMock()
    client.get_queue_url.return_value = {
        "QueueUrl": "https://sqs.us-west-2.example/queue",
    }
    client.send_message.side_effect = ClientError(
        {
            "Error": {
                "Code": "AccessDenied",
                "Message": "denied",
            }
        },
        "SendMessage",
    )

    transport = SqsRegionalTransport(
        client_factory=MagicMock(return_value=client),
        queue_names_by_region={
            "us-west-2": "west-processing",
        },
    )

    result = transport.deliver(request())

    assert result.status == DeliveryStatus.DELIVERY_FAILED
    assert not result.delivered
    client.send_message.assert_called_once()


def test_delivery_request_rejects_blank_owner_region():
    try:
        RegionalDeliveryRequest(
            current_region="us-east-1",
            owner_region=" ",
            payload={},
            request_id="request-123",
            delivery_type="processing_queue",
        )
    except ValueError as error:
        assert "owner_region" in str(error)
    else:
        raise AssertionError("Expected ValueError")
