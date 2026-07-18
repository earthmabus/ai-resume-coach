from __future__ import annotations

import json
from decimal import Decimal
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from core.outbox import (
    OUTBOX_STATUS_DISPATCHING,
    OUTBOX_STATUS_FAILED_PERMANENT,
    OUTBOX_STATUS_FAILED_RETRYABLE,
    OUTBOX_STATUS_PENDING,
)
from core.outbox_publisher import (
    ClaimResult,
    DynamoDbOutboxRepository,
    OutboxPublisher,
    DEFAULT_DELIVERED_RETENTION_SECONDS,
    PublishResult,
    SqsEventPublisher,
    retry_delay_seconds,
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
        "createdRegion": "us-east-1",
        "ownerRegion": "us-east-1",
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
    assert message["ownerRegion"] == "us-east-1"


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
    assert result.claimed == 1
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

    assert result.examined == 1
    assert result.claimed == 1
    assert result.failed == 1
    assert result.published == 0
    assert result.skipped == 0

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

    assert result.examined == 1
    assert result.claimed == 0
    assert result.skipped == 1
    assert result.published == 0
    assert result.failed == 0
    event_publisher.publish.assert_not_called()


def test_publish_result_counts_remain_consistent():
    result = PublishResult(
        examined=7,
        claimed=5,
        published=4,
        failed=1,
        skipped=2,
    )

    assert result.claimed == (
        result.published + result.failed
    )

    assert result.examined == (
        result.claimed + result.skipped
    )

def test_sqs_publisher_serializes_dynamodb_decimals():
    client = MagicMock()
    client.send_message.return_value = {
        "MessageId": "message-123",
    }

    publisher = SqsEventPublisher(
        client=client,
        queue_url="https://example.com/queue",
    )

    item = event_item()
    item["eventVersion"] = Decimal("1")
    item["payload"] = {
        **item["payload"],
        "schemaVersion": Decimal("1"),
        "retryScore": Decimal("0.75"),
        "nested": {
            "count": Decimal("2"),
        },
        "values": [
            Decimal("3"),
            Decimal("4.5"),
        ],
    }

    message_id = publisher.publish(item)

    assert message_id == "message-123"

    message = json.loads(
        client.send_message.call_args.kwargs[
            "MessageBody"
        ]
    )

    assert message["eventVersion"] == 1
    assert message["schemaVersion"] == 1
    assert message["retryScore"] == 0.75
    assert message["nested"]["count"] == 2
    assert message["values"] == [3, 4.5]

@pytest.mark.parametrize(
    "delivery_attempts,expected_delay",
    [
        (1, 60),
        (2, 120),
        (3, 240),
        (4, 480),
        (5, 900),
        (6, 1800),
        (20, 1800),
    ],
)
def test_retry_delay_seconds_uses_expected_schedule(
    delivery_attempts,
    expected_delay,
):
    assert (
        retry_delay_seconds(delivery_attempts)
        == expected_delay
    )


def test_retry_delay_seconds_normalizes_non_positive_attempts():
    assert retry_delay_seconds(0) == 60
    assert retry_delay_seconds(-5) == 60


def test_list_dispatchable_filters_future_retries():
    table = MagicMock()

    pending = event_item(OUTBOX_STATUS_PENDING)
    ready_retry = {
        **event_item(OUTBOX_STATUS_FAILED_RETRYABLE),
        "eventId": "event-ready",
        "nextDeliveryAttemptAt": NOW_EPOCH,
    }
    future_retry = {
        **event_item(OUTBOX_STATUS_FAILED_RETRYABLE),
        "eventId": "event-future",
        "nextDeliveryAttemptAt": NOW_EPOCH + 60,
    }
    legacy_retry = {
        **event_item(OUTBOX_STATUS_FAILED_RETRYABLE),
        "eventId": "event-legacy",
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
        {
            "Items": [
                ready_retry,
                future_retry,
                legacy_retry,
            ]
        },
        {
            "Items": [
                active_dispatch,
                stale_dispatch,
            ]
        },
    ]

    repository = make_repository(table)

    results = repository.list_dispatchable(limit=10)

    assert results == [
        pending,
        ready_retry,
        legacy_retry,
        stale_dispatch,
    ]


def test_list_dispatchable_paginates_past_ineligible_retry():
    table = MagicMock()

    future_retry = {
        **event_item(OUTBOX_STATUS_FAILED_RETRYABLE),
        "eventId": "event-future",
        "nextDeliveryAttemptAt": NOW_EPOCH + 600,
    }
    ready_retry = {
        **event_item(OUTBOX_STATUS_FAILED_RETRYABLE),
        "eventId": "event-ready",
        "nextDeliveryAttemptAt": NOW_EPOCH,
    }

    table.query.side_effect = [
        {"Items": []},
        {
            "Items": [future_retry],
            "LastEvaluatedKey": {
                "pk": "OUTBOX#event-future",
                "sk": "OUTBOX#event-future",
                "gsi1pk": "OUTBOX_STATUS#FAILED_RETRYABLE",
                "gsi1sk": (
                    "2026-07-15T19:00:00+00:00#event-future"
                ),
            },
        },
        {"Items": [ready_retry]},
    ]

    repository = make_repository(table)

    results = repository.list_dispatchable(limit=1)

    assert results == [ready_retry]
    assert table.query.call_count == 3
    assert (
        "ExclusiveStartKey"
        in table.query.call_args_list[2].kwargs
    )


def test_claim_retryable_requires_elapsed_retry_time():
    table = MagicMock()
    claimed = {
        **event_item(OUTBOX_STATUS_DISPATCHING),
        "deliveryAttempts": 2,
        "version": 2,
    }
    table.update_item.return_value = {
        "Attributes": claimed,
    }

    item = {
        **event_item(OUTBOX_STATUS_FAILED_RETRYABLE),
        "nextDeliveryAttemptAt": NOW_EPOCH,
    }

    repository = make_repository(table)
    result = repository.claim(item)

    assert result.claimed is True

    arguments = table.update_item.call_args.kwargs
    assert "nextDeliveryAttemptAt <= :nowEpoch" in (
        arguments["ConditionExpression"]
    )
    assert "REMOVE nextDeliveryAttemptAt" in (
        arguments["UpdateExpression"]
    )
    assert (
        arguments["ExpressionAttributeValues"][":nowEpoch"]
        == NOW_EPOCH
    )


@pytest.mark.parametrize(
    "delivery_attempts,expected_delay",
    [
        (1, 60),
        (2, 120),
        (3, 240),
        (4, 480),
        (5, 900),
        (6, 1800),
    ],
)
def test_mark_failed_retryable_schedules_next_attempt(
    delivery_attempts,
    expected_delay,
):
    table = MagicMock()
    table.update_item.return_value = {
        "Attributes": {
            **event_item(OUTBOX_STATUS_FAILED_RETRYABLE),
            "lastDeliveryError": "SQS unavailable",
        }
    }

    item = {
        **event_item(OUTBOX_STATUS_DISPATCHING),
        "deliveryAttempts": delivery_attempts,
    }

    repository = make_repository(table)
    repository.mark_failed_retryable(
        item=item,
        attempt_id="attempt-123",
        error_message="SQS unavailable",
    )

    arguments = table.update_item.call_args.kwargs
    values = arguments["ExpressionAttributeValues"]

    assert values[":nextAttemptAt"] == (
        NOW_EPOCH + expected_delay
    )
    assert "nextDeliveryAttemptAt = :nextAttemptAt" in (
        arguments["UpdateExpression"]
    )


def test_mark_failed_retryable_defaults_to_first_delay():
    table = MagicMock()
    table.update_item.return_value = {
        "Attributes": event_item(
            OUTBOX_STATUS_FAILED_RETRYABLE
        )
    }

    item = event_item(OUTBOX_STATUS_DISPATCHING)
    item.pop("deliveryAttempts")

    repository = make_repository(table)
    repository.mark_failed_retryable(
        item=item,
        attempt_id="attempt-123",
        error_message="SQS unavailable",
    )

    values = table.update_item.call_args.kwargs[
        "ExpressionAttributeValues"
    ]

    assert values[":nextAttemptAt"] == NOW_EPOCH + 60


def test_mark_delivered_removes_retry_schedule():
    table = MagicMock()
    table.update_item.return_value = {
        "Attributes": {
            **event_item(),
            "status": "DELIVERED",
        }
    }

    repository = make_repository(table)
    repository.mark_delivered(
        item=event_item(OUTBOX_STATUS_DISPATCHING),
        attempt_id="attempt-123",
        message_id="message-123",
    )

    update_expression = table.update_item.call_args.kwargs[
        "UpdateExpression"
    ]

    assert "nextDeliveryAttemptAt" in update_expression

def test_outbox_publisher_rejects_non_positive_max_workers():
    repository = MagicMock()
    event_publisher = MagicMock()

    with pytest.raises(
        ValueError,
        match="max_workers must be greater than zero",
    ):
        OutboxPublisher(
            repository=repository,
            event_publisher=event_publisher,
            max_workers=0,
        )


def test_outbox_publisher_publishes_multiple_claimed_events():
    repository = MagicMock()

    events = [
        {
            **event_item(),
            "eventId": f"event-{index}",
            "pk": f"OUTBOX#event-{index}",
            "sk": f"OUTBOX#event-{index}",
        }
        for index in range(4)
    ]

    claimed_items = [
        {
            **event,
            "status": OUTBOX_STATUS_DISPATCHING,
            "dispatchAttemptId": f"attempt-{index}",
        }
        for index, event in enumerate(events)
    ]

    repository.list_dispatchable.return_value = events
    repository.claim.side_effect = [
        ClaimResult(
            claimed=True,
            item=claimed_item,
            attempt_id=f"attempt-{index}",
        )
        for index, claimed_item in enumerate(
            claimed_items
        )
    ]

    event_publisher = MagicMock()
    event_publisher.publish.side_effect = [
        f"message-{index}"
        for index in range(4)
    ]

    publisher = OutboxPublisher(
        repository=repository,
        event_publisher=event_publisher,
        batch_size=25,
        max_workers=4,
    )

    result = publisher.publish_pending()

    assert result == PublishResult(
        examined=4,
        claimed=4,
        published=4,
        failed=0,
        skipped=0,
    )

    assert repository.claim.call_count == 4
    assert event_publisher.publish.call_count == 4
    assert repository.mark_delivered.call_count == 4
    repository.mark_failed_retryable.assert_not_called()


def test_outbox_publisher_counts_mixed_parallel_outcomes():
    repository = MagicMock()

    events = [
        {
            **event_item(),
            "eventId": f"event-{index}",
            "pk": f"OUTBOX#event-{index}",
            "sk": f"OUTBOX#event-{index}",
        }
        for index in range(3)
    ]

    claimed_items = [
        {
            **event,
            "status": OUTBOX_STATUS_DISPATCHING,
            "dispatchAttemptId": f"attempt-{index}",
        }
        for index, event in enumerate(events)
    ]

    repository.list_dispatchable.return_value = events
    repository.claim.side_effect = [
        ClaimResult(
            claimed=True,
            item=claimed_items[0],
            attempt_id="attempt-0",
        ),
        ClaimResult(
            claimed=True,
            item=claimed_items[1],
            attempt_id="attempt-1",
        ),
        ClaimResult(
            claimed=True,
            item=claimed_items[2],
            attempt_id="attempt-2",
        ),
    ]

    def publish_side_effect(item):
        if item["eventId"] == "event-1":
            raise RuntimeError("SQS unavailable")

        return f"message-{item['eventId']}"

    event_publisher = MagicMock()
    event_publisher.publish.side_effect = (
        publish_side_effect
    )

    publisher = OutboxPublisher(
        repository=repository,
        event_publisher=event_publisher,
        max_workers=3,
    )

    result = publisher.publish_pending()

    assert result == PublishResult(
        examined=3,
        claimed=3,
        published=2,
        failed=1,
        skipped=0,
    )

    assert repository.mark_delivered.call_count == 2
    repository.mark_failed_retryable.assert_called_once()

    failure_arguments = (
        repository.mark_failed_retryable
        .call_args.kwargs
    )

    assert (
        failure_arguments["item"]["eventId"]
        == "event-1"
    )
    assert (
        failure_arguments["attempt_id"]
        == "attempt-1"
    )
    assert (
        failure_arguments["error_message"]
        == "SQS unavailable"
    )


def test_outbox_publisher_preserves_skips_with_parallel_work():
    repository = MagicMock()

    first_event = {
        **event_item(),
        "eventId": "event-first",
        "pk": "OUTBOX#event-first",
        "sk": "OUTBOX#event-first",
    }
    skipped_event = {
        **event_item(),
        "eventId": "event-skipped",
        "pk": "OUTBOX#event-skipped",
        "sk": "OUTBOX#event-skipped",
    }
    second_event = {
        **event_item(),
        "eventId": "event-second",
        "pk": "OUTBOX#event-second",
        "sk": "OUTBOX#event-second",
    }

    repository.list_dispatchable.return_value = [
        first_event,
        skipped_event,
        second_event,
    ]

    repository.claim.side_effect = [
        ClaimResult(
            claimed=True,
            item={
                **first_event,
                "status": OUTBOX_STATUS_DISPATCHING,
            },
            attempt_id="attempt-first",
        ),
        ClaimResult(claimed=False),
        ClaimResult(
            claimed=True,
            item={
                **second_event,
                "status": OUTBOX_STATUS_DISPATCHING,
            },
            attempt_id="attempt-second",
        ),
    ]

    event_publisher = MagicMock()
    event_publisher.publish.side_effect = [
        "message-first",
        "message-second",
    ]

    publisher = OutboxPublisher(
        repository=repository,
        event_publisher=event_publisher,
        max_workers=2,
    )

    result = publisher.publish_pending()

    assert result == PublishResult(
        examined=3,
        claimed=2,
        published=2,
        failed=0,
        skipped=1,
    )

    assert event_publisher.publish.call_count == 2
    assert repository.mark_delivered.call_count == 2


def test_publish_claimed_event_marks_success_delivered():
    repository = MagicMock()
    event_publisher = MagicMock()
    event_publisher.publish.return_value = (
        "message-123"
    )

    publisher = OutboxPublisher(
        repository=repository,
        event_publisher=event_publisher,
        max_workers=2,
    )

    from core.outbox_publisher import ClaimedEvent

    claimed_event = ClaimedEvent(
        item=event_item(
            OUTBOX_STATUS_DISPATCHING
        ),
        attempt_id="attempt-123",
    )

    result = publisher._publish_claimed_event(
        claimed_event
    )

    assert result.published is True
    repository.mark_delivered.assert_called_once_with(
        item=claimed_event.item,
        attempt_id="attempt-123",
        message_id="message-123",
    )
    repository.mark_failed_retryable.assert_not_called()


def test_publish_claimed_event_marks_failure_retryable():
    repository = MagicMock()
    event_publisher = MagicMock()
    event_publisher.publish.side_effect = RuntimeError(
        "transport failed"
    )

    publisher = OutboxPublisher(
        repository=repository,
        event_publisher=event_publisher,
        max_workers=2,
    )

    from core.outbox_publisher import ClaimedEvent

    claimed_event = ClaimedEvent(
        item=event_item(
            OUTBOX_STATUS_DISPATCHING
        ),
        attempt_id="attempt-123",
    )

    result = publisher._publish_claimed_event(
        claimed_event
    )

    assert result.published is False
    repository.mark_failed_retryable.assert_called_once_with(
        item=claimed_event.item,
        attempt_id="attempt-123",
        error_message="transport failed",
    )
    repository.mark_delivered.assert_not_called()


def test_repository_rejects_non_positive_delivered_retention():
    with pytest.raises(
        ValueError,
        match="delivered_retention_seconds must be greater than zero",
    ):
        DynamoDbOutboxRepository(
            table=MagicMock(),
            region="us-east-1",
            delivered_retention_seconds=0,
        )


def test_mark_delivered_sets_ttl():
    table = MagicMock()
    table.update_item.return_value = {
        "Attributes": {
            **event_item(),
            "status": "DELIVERED",
        }
    }
    repository = make_repository(table)

    repository.mark_delivered(
        item=event_item(OUTBOX_STATUS_DISPATCHING),
        attempt_id="attempt-123",
        message_id="message-123",
    )

    values = table.update_item.call_args.kwargs[
        "ExpressionAttributeValues"
    ]
    assert values[":expiresAt"] == (
        NOW_EPOCH + DEFAULT_DELIVERED_RETENTION_SECONDS
    )


def test_mark_failed_permanent_removes_dispatch_index():
    table = MagicMock()
    table.update_item.return_value = {
        "Attributes": {
            **event_item(),
            "status": OUTBOX_STATUS_FAILED_PERMANENT,
        }
    }
    repository = make_repository(table)

    result = repository.mark_failed_permanent(
        item=event_item(OUTBOX_STATUS_DISPATCHING),
        attempt_id="attempt-123",
        error_message="terminal failure",
    )

    assert result["status"] == OUTBOX_STATUS_FAILED_PERMANENT
    arguments = table.update_item.call_args.kwargs
    assert "REMOVE gsi1pk, gsi1sk" in arguments["UpdateExpression"]
    assert arguments["ExpressionAttributeValues"][
        ":failedPermanent"
    ] == OUTBOX_STATUS_FAILED_PERMANENT


def test_publisher_marks_failure_retryable_below_attempt_limit():
    claimed_item = {
        **event_item(OUTBOX_STATUS_DISPATCHING),
        "deliveryAttempts": 19,
    }
    repository = MagicMock()
    repository.list_dispatchable.return_value = [event_item()]
    repository.claim.return_value = ClaimResult(
        claimed=True,
        item=claimed_item,
        attempt_id="attempt-123",
    )
    transport = MagicMock()
    transport.publish.side_effect = RuntimeError("SQS unavailable")

    result = OutboxPublisher(
        repository=repository,
        event_publisher=transport,
        max_delivery_attempts=20,
    ).publish_pending()

    assert result.failed == 1
    assert result.permanently_failed == 0
    repository.mark_failed_retryable.assert_called_once()
    repository.mark_failed_permanent.assert_not_called()


def test_publisher_marks_failure_permanent_at_attempt_limit():
    claimed_item = {
        **event_item(OUTBOX_STATUS_DISPATCHING),
        "deliveryAttempts": 20,
    }
    repository = MagicMock()
    repository.list_dispatchable.return_value = [event_item()]
    repository.claim.return_value = ClaimResult(
        claimed=True,
        item=claimed_item,
        attempt_id="attempt-123",
    )
    transport = MagicMock()
    transport.publish.side_effect = RuntimeError("SQS unavailable")

    result = OutboxPublisher(
        repository=repository,
        event_publisher=transport,
        max_delivery_attempts=20,
    ).publish_pending()

    assert result.failed == 1
    assert result.permanently_failed == 1
    repository.mark_failed_permanent.assert_called_once_with(
        item=claimed_item,
        attempt_id="attempt-123",
        error_message="SQS unavailable",
    )
    repository.mark_failed_retryable.assert_not_called()


def test_publisher_rejects_non_positive_attempt_limit():
    with pytest.raises(
        ValueError,
        match="max_delivery_attempts must be greater than zero",
    ):
        OutboxPublisher(
            repository=MagicMock(),
            event_publisher=MagicMock(),
            max_delivery_attempts=0,
        )
