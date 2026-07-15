from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from core.outbox import (
    OUTBOX_STATUS_DISPATCHING,
    OUTBOX_STATUS_FAILED_RETRYABLE,
    OUTBOX_STATUS_PENDING,
)
from core.outbox_publisher import (
    ClaimResult,
    DynamoDbOutboxRepository,
    OutboxPublisher,
    SqsEventPublisher,
)


NOW = datetime(2026, 7, 15, 20, 0, tzinfo=timezone.utc)
NOW_EPOCH = int(NOW.timestamp())
EVENT_ID = "event-123"


def event_item(status=OUTBOX_STATUS_PENDING) -> dict:
    return {
        "pk": f"OUTBOX#{EVENT_ID}",
        "sk": f"OUTBOX#{EVENT_ID}",
        "recordType": "outboxEvent",
        "eventId": EVENT_ID,
        "eventType": "RESUME_ANALYSIS_REQUESTED",
        "eventVersion": 1,
        "jobType": "resumeAnalysis",
        "payload": {
            "schemaVersion": 1,
            "jobType": "resumeAnalysis",
            "jobId": "analysis-123",
            "analysisId": "analysis-123",
            "userId": "user-123",
        },
        "status": status,
        "createdAt": "2026-07-15T19:00:00+00:00",
        "createdByRequestId": "request-123",
        "deliveryAttempts": 0,
        "version": 1,
        "gsi1pk": f"OUTBOX_STATUS#{status}",
        "gsi1sk": f"2026-07-15T19:00:00+00:00#{EVENT_ID}",
    }


def conditional_failure() -> ClientError:
    return ClientError(
        {
            "Error": {
                "Code": "ConditionalCheckFailedException",
                "Message": "condition failed",
            }
        },
        "UpdateItem",
    )


def make_repository(table: MagicMock) -> DynamoDbOutboxRepository:
    return DynamoDbOutboxRepository(
        table=table,
        region="us-east-1",
        lease_seconds=300,
        now=lambda: NOW,
        epoch_seconds=lambda: NOW_EPOCH,
    )


def test_list_dispatchable_queries_pending_retryable_and_stale_claims():
    table = MagicMock()
    pending = event_item(OUTBOX_STATUS_PENDING)
    retryable = {
        **event_item(OUTBOX_STATUS_FAILED_RETRYABLE),
        "eventId": "event-456",
    }
    active_dispatch = {
        **event_item(OUTBOX_STATUS_DISPATCHING),
        "eventId": "event-active",
        "dispatchLeaseExpiresAt": NOW_EPOCH + 60,
    }
    stale_dispatch = {
        **event_item(OUTBOX_STATUS_DISPATCHING),
        "eventId": "event-stale",
        "dispatchLeaseExpiresAt": NOW_EPOCH - 1,
    }

    table.query.side_effect = [
        {"Items": [pending]},
        {"Items": [retryable]},
        {"Items": [active_dispatch, stale_dispatch]},
    ]

    repository = make_repository(table)

    results = repository.list_dispatchable(limit=10)

    assert results == [pending, retryable, stale_dispatch]
    assert table.query.call_count == 3


@pytest.mark.parametrize(
    "status",
    [OUTBOX_STATUS_PENDING, OUTBOX_STATUS_FAILED_RETRYABLE],
)
def test_claim_moves_dispatchable_event_to_dispatching(status):
    table = MagicMock()
    claimed = {
        **event_item(OUTBOX_STATUS_DISPATCHING),
        "dispatchAttemptId": "attempt-123",
        "deliveryAttempts": 1,
        "version": 2,
    }
    table.update_item.return_value = {"Attributes": claimed}

    repository = make_repository(table)
    result = repository.claim(event_item(status))

    assert result.claimed is True
    assert result.item == claimed
    assert result.attempt_id

    arguments = table.update_item.call_args.kwargs
    assert arguments["ExpressionAttributeValues"][":expectedStatus"] == status
    assert (
        arguments["ExpressionAttributeValues"][":dispatching"]
        == OUTBOX_STATUS_DISPATCHING
    )


def test_claim_reclaims_only_expired_dispatching_event():
    table = MagicMock()
    stale = {
        **event_item(OUTBOX_STATUS_DISPATCHING),
        "dispatchLeaseExpiresAt": NOW_EPOCH - 1,
    }
    table.update_item.return_value = {
        "Attributes": {
            **stale,
            "dispatchLeaseExpiresAt": NOW_EPOCH + 300,
        }
    }

    repository = make_repository(table)
    result = repository.claim(stale)

    assert result.claimed is True
    condition = table.update_item.call_args.kwargs[
        "ConditionExpression"
    ]
    assert "dispatchLeaseExpiresAt <= :nowEpoch" in condition


def test_claim_race_is_skipped():
    table = MagicMock()
    table.update_item.side_effect = conditional_failure()

    repository = make_repository(table)
    result = repository.claim(event_item())

    assert result == ClaimResult(claimed=False)


def test_mark_delivered_removes_sparse_index_and_claim_metadata():
    table = MagicMock()
    delivered = {
        **event_item(),
        "status": "DELIVERED",
        "transportMessageId": "message-123",
    }
    table.update_item.return_value = {"Attributes": delivered}

    repository = make_repository(table)
    result = repository.mark_delivered(
        item=event_item(OUTBOX_STATUS_DISPATCHING),
        attempt_id="attempt-123",
        message_id="message-123",
    )

    assert result == delivered
    arguments = table.update_item.call_args.kwargs
    assert "REMOVE gsi1pk, gsi1sk" in arguments["UpdateExpression"]
    assert (
        arguments["ExpressionAttributeValues"][":messageId"]
        == "message-123"
    )


def test_mark_failed_retryable_restores_retry_index():
    table = MagicMock()
    failed = {
        **event_item(OUTBOX_STATUS_FAILED_RETRYABLE),
        "lastDeliveryError": "SQS unavailable",
    }
    table.update_item.return_value = {"Attributes": failed}

    repository = make_repository(table)
    result = repository.mark_failed_retryable(
        item=event_item(OUTBOX_STATUS_DISPATCHING),
        attempt_id="attempt-123",
        error_message="SQS unavailable",
    )

    assert result == failed
    values = table.update_item.call_args.kwargs[
        "ExpressionAttributeValues"
    ]
    assert values[":failedRetryablePk"] == (
        "OUTBOX_STATUS#FAILED_RETRYABLE"
    )


def test_sqs_publisher_preserves_worker_payload_and_adds_trace_metadata():
    client = MagicMock()
    client.send_message.return_value = {"MessageId": "message-123"}

    publisher = SqsEventPublisher(
        client=client,
        queue_url="https://example.com/queue",
    )

    message_id = publisher.publish(event_item())

    assert message_id == "message-123"
    call = client.send_message.call_args.kwargs
    message = json.loads(call["MessageBody"])

    assert message["jobType"] == "resumeAnalysis"
    assert message["analysisId"] == "analysis-123"
    assert message["outboxEventId"] == EVENT_ID
    assert message["eventType"] == "RESUME_ANALYSIS_REQUESTED"
    assert message["requestId"] == "request-123"


def test_sqs_publisher_requires_message_id():
    client = MagicMock()
    client.send_message.return_value = {}

    publisher = SqsEventPublisher(
        client=client,
        queue_url="https://example.com/queue",
    )

    with pytest.raises(
        RuntimeError,
        match="SQS did not return a MessageId",
    ):
        publisher.publish(event_item())


def test_outbox_publisher_marks_success_delivered():
    claimed_item = event_item(OUTBOX_STATUS_DISPATCHING)
    repository = MagicMock()
    repository.list_dispatchable.return_value = [event_item()]
    repository.claim.return_value = ClaimResult(
        claimed=True,
        item=claimed_item,
        attempt_id="attempt-123",
    )

    event_publisher = MagicMock()
    event_publisher.publish.return_value = "message-123"

    publisher = OutboxPublisher(
        repository=repository,
        event_publisher=event_publisher,
        batch_size=25,
    )

    result = publisher.publish_pending()

    assert result.examined == 1
    assert result.published == 1
    assert result.failed == 0
    assert result.skipped == 0

    repository.mark_delivered.assert_called_once_with(
        item=claimed_item,
        attempt_id="attempt-123",
        message_id="message-123",
    )
    repository.mark_failed_retryable.assert_not_called()


def test_outbox_publisher_marks_transport_failure_retryable():
    claimed_item = event_item(OUTBOX_STATUS_DISPATCHING)
    repository = MagicMock()
    repository.list_dispatchable.return_value = [event_item()]
    repository.claim.return_value = ClaimResult(
        claimed=True,
        item=claimed_item,
        attempt_id="attempt-123",
    )

    event_publisher = MagicMock()
    event_publisher.publish.side_effect = RuntimeError(
        "SQS unavailable"
    )

    publisher = OutboxPublisher(
        repository=repository,
        event_publisher=event_publisher,
    )

    result = publisher.publish_pending()

    assert result.failed == 1
    assert result.published == 0
    repository.mark_failed_retryable.assert_called_once_with(
        item=claimed_item,
        attempt_id="attempt-123",
        error_message="SQS unavailable",
    )
    repository.mark_delivered.assert_not_called()


def test_outbox_publisher_counts_claim_race_as_skipped():
    repository = MagicMock()
    repository.list_dispatchable.return_value = [event_item()]
    repository.claim.return_value = ClaimResult(claimed=False)

    event_publisher = MagicMock()
    publisher = OutboxPublisher(
        repository=repository,
        event_publisher=event_publisher,
    )

    result = publisher.publish_pending()

    assert result.skipped == 1
    assert result.published == 0
    event_publisher.publish.assert_not_called()
