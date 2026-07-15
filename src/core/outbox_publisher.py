from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from core.keys import outbox_status_pk
from core.outbox import (
    OUTBOX_STATUS_DELIVERED,
    OUTBOX_STATUS_DISPATCHING,
    OUTBOX_STATUS_FAILED_RETRYABLE,
    OUTBOX_STATUS_PENDING,
)


DEFAULT_DISPATCH_LEASE_SECONDS = 300
DEFAULT_BATCH_SIZE = 25
MAX_ERROR_MESSAGE_LENGTH = 2000


@dataclass(frozen=True)
class PublishResult:
    examined: int = 0
    published: int = 0
    failed: int = 0
    skipped: int = 0


@dataclass(frozen=True)
class ClaimResult:
    claimed: bool
    item: dict[str, Any] | None = None
    attempt_id: str | None = None


class DynamoDbOutboxRepository:
    """Persistence operations for dispatchable outbox records."""

    def __init__(
        self,
        *,
        table: Any,
        region: str,
        lease_seconds: int = DEFAULT_DISPATCH_LEASE_SECONDS,
        now: Callable[[], datetime] | None = None,
        epoch_seconds: Callable[[], int] | None = None,
    ) -> None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be greater than zero")

        self._table = table
        self._region = str(region or "").strip() or "unknown"
        self._lease_seconds = lease_seconds
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._epoch_seconds = epoch_seconds or (
            lambda: int(time.time())
        )

    def list_dispatchable(
        self,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        """
        Return a bounded set of records that can be attempted.

        PENDING and FAILED_RETRYABLE records are immediately dispatchable.
        DISPATCHING records are included only when their lease has expired,
        allowing recovery after a publisher crashes.
        """
        if limit <= 0:
            return []

        results: list[dict[str, Any]] = []
        now_epoch = self._epoch_seconds()

        for status in (
            OUTBOX_STATUS_PENDING,
            OUTBOX_STATUS_FAILED_RETRYABLE,
            OUTBOX_STATUS_DISPATCHING,
        ):
            remaining = limit - len(results)

            if remaining <= 0:
                break

            response = self._table.query(
                IndexName="gsi1",
                KeyConditionExpression=Key("gsi1pk").eq(
                    outbox_status_pk(status)
                ),
                Limit=remaining,
                ScanIndexForward=True,
            )

            for item in response.get("Items", []):
                if status == OUTBOX_STATUS_DISPATCHING:
                    lease_expires_at = int(
                        item.get("dispatchLeaseExpiresAt", 0)
                    )

                    if lease_expires_at > now_epoch:
                        continue

                results.append(item)

                if len(results) >= limit:
                    break

        return results

    def claim(
        self,
        item: dict[str, Any],
    ) -> ClaimResult:
        event_id = str(item.get("eventId") or "").strip()
        current_status = str(item.get("status") or "").strip()
        current_version = int(item.get("version", 0))

        if not event_id:
            raise ValueError("outbox eventId is required")

        if current_status not in {
            OUTBOX_STATUS_PENDING,
            OUTBOX_STATUS_FAILED_RETRYABLE,
            OUTBOX_STATUS_DISPATCHING,
        }:
            return ClaimResult(claimed=False)

        attempt_id = str(uuid.uuid4())
        now = self._now().isoformat()
        now_epoch = self._epoch_seconds()
        lease_expires_at = now_epoch + self._lease_seconds

        condition_expression = (
            "#status = :expectedStatus "
            "AND ("
            "#version = :expectedVersion "
            "OR ("
            "attribute_not_exists(#version) "
            "AND :expectedVersion = :zero"
            ")"
            ")"
        )

        values: dict[str, Any] = {
            ":dispatching": OUTBOX_STATUS_DISPATCHING,
            ":dispatchingPk": outbox_status_pk(
                OUTBOX_STATUS_DISPATCHING
            ),
            ":attemptId": attempt_id,
            ":now": now,
            ":leaseExpiresAt": lease_expires_at,
            ":region": self._region,
            ":expectedStatus": current_status,
            ":expectedVersion": current_version,
            ":zero": 0,
            ":one": 1,
        }

        if current_status == OUTBOX_STATUS_DISPATCHING:
            condition_expression += (
                " AND dispatchLeaseExpiresAt <= :nowEpoch"
            )
            values[":nowEpoch"] = now_epoch

        try:
            response = self._table.update_item(
                Key={
                    "pk": item["pk"],
                    "sk": item["sk"],
                },
                UpdateExpression=(
                    "SET #status = :dispatching, "
                    "gsi1pk = :dispatchingPk, "
                    "dispatchAttemptId = :attemptId, "
                    "dispatchStartedAt = :now, "
                    "dispatchLeaseExpiresAt = :leaseExpiresAt, "
                    "updatedAt = :now, "
                    "updatedByRequestId = :attemptId, "
                    "lastUpdatedRegion = :region, "
                    "deliveryAttempts = "
                    "if_not_exists(deliveryAttempts, :zero) + :one, "
                    "#version = if_not_exists(#version, :zero) + :one"
                ),
                ConditionExpression=condition_expression,
                ExpressionAttributeNames={
                    "#status": "status",
                    "#version": "version",
                },
                ExpressionAttributeValues=values,
                ReturnValues="ALL_NEW",
            )
        except ClientError as error:
            if self._is_conditional_failure(error):
                return ClaimResult(claimed=False)

            raise

        return ClaimResult(
            claimed=True,
            item=response["Attributes"],
            attempt_id=attempt_id,
        )

    def mark_delivered(
        self,
        *,
        item: dict[str, Any],
        attempt_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        now = self._now().isoformat()

        response = self._table.update_item(
            Key={
                "pk": item["pk"],
                "sk": item["sk"],
            },
            UpdateExpression=(
                "SET #status = :delivered, "
                "deliveredAt = :now, "
                "updatedAt = :now, "
                "updatedByRequestId = :attemptId, "
                "lastUpdatedRegion = :region, "
                "transportMessageId = :messageId, "
                "#version = if_not_exists(#version, :zero) + :one "
                "REMOVE gsi1pk, gsi1sk, "
                "dispatchAttemptId, dispatchStartedAt, "
                "dispatchLeaseExpiresAt, lastDeliveryError, "
                "lastDeliveryFailedAt"
            ),
            ConditionExpression=(
                "#status = :dispatching "
                "AND dispatchAttemptId = :attemptId"
            ),
            ExpressionAttributeNames={
                "#status": "status",
                "#version": "version",
            },
            ExpressionAttributeValues={
                ":delivered": OUTBOX_STATUS_DELIVERED,
                ":dispatching": OUTBOX_STATUS_DISPATCHING,
                ":attemptId": attempt_id,
                ":messageId": message_id,
                ":now": now,
                ":region": self._region,
                ":zero": 0,
                ":one": 1,
            },
            ReturnValues="ALL_NEW",
        )

        return response["Attributes"]

    def mark_failed_retryable(
        self,
        *,
        item: dict[str, Any],
        attempt_id: str,
        error_message: str,
    ) -> dict[str, Any] | None:
        now = self._now().isoformat()
        truncated_error = str(error_message or "")[:MAX_ERROR_MESSAGE_LENGTH]

        try:
            response = self._table.update_item(
                Key={
                    "pk": item["pk"],
                    "sk": item["sk"],
                },
                UpdateExpression=(
                    "SET #status = :failedRetryable, "
                    "gsi1pk = :failedRetryablePk, "
                    "lastDeliveryError = :errorMessage, "
                    "lastDeliveryFailedAt = :now, "
                    "updatedAt = :now, "
                    "updatedByRequestId = :attemptId, "
                    "lastUpdatedRegion = :region, "
                    "#version = if_not_exists(#version, :zero) + :one "
                    "REMOVE dispatchAttemptId, dispatchStartedAt, "
                    "dispatchLeaseExpiresAt"
                ),
                ConditionExpression=(
                    "#status = :dispatching "
                    "AND dispatchAttemptId = :attemptId"
                ),
                ExpressionAttributeNames={
                    "#status": "status",
                    "#version": "version",
                },
                ExpressionAttributeValues={
                    ":failedRetryable": (
                        OUTBOX_STATUS_FAILED_RETRYABLE
                    ),
                    ":failedRetryablePk": outbox_status_pk(
                        OUTBOX_STATUS_FAILED_RETRYABLE
                    ),
                    ":dispatching": OUTBOX_STATUS_DISPATCHING,
                    ":attemptId": attempt_id,
                    ":errorMessage": truncated_error,
                    ":now": now,
                    ":region": self._region,
                    ":zero": 0,
                    ":one": 1,
                },
                ReturnValues="ALL_NEW",
            )
        except ClientError as error:
            if self._is_conditional_failure(error):
                return None

            raise

        return response["Attributes"]

    @staticmethod
    def _is_conditional_failure(error: ClientError) -> bool:
        return (
            error.response.get("Error", {}).get("Code")
            == "ConditionalCheckFailedException"
        )


class SqsEventPublisher:
    """Publish outbox payloads to the existing worker queue."""

    def __init__(
        self,
        *,
        client: Any,
        queue_url: str,
    ) -> None:
        normalized_queue_url = str(queue_url or "").strip()

        if not normalized_queue_url:
            raise ValueError("queue_url is required")

        self._client = client
        self._queue_url = normalized_queue_url

    def publish(self, item: dict[str, Any]) -> str:
        payload = item.get("payload")

        if not isinstance(payload, dict):
            raise ValueError("outbox payload must be a dictionary")

        message = {
            **payload,
            "outboxEventId": item["eventId"],
            "eventType": item["eventType"],
            "eventVersion": item["eventVersion"],
            "requestId": item.get("createdByRequestId", ""),
            "submittedAt": item.get("createdAt", ""),
        }

        response = self._client.send_message(
            QueueUrl=self._queue_url,
            MessageBody=json.dumps(
                message,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
        )

        message_id = str(response.get("MessageId") or "").strip()

        if not message_id:
            raise RuntimeError("SQS did not return a MessageId")

        return message_id


class OutboxPublisher:
    """Coordinate query, claim, transport publication, and status updates."""

    def __init__(
        self,
        *,
        repository: DynamoDbOutboxRepository,
        event_publisher: SqsEventPublisher,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")

        self._repository = repository
        self._event_publisher = event_publisher
        self._batch_size = batch_size

    def publish_pending(self) -> PublishResult:
        events = self._repository.list_dispatchable(
            limit=self._batch_size,
        )

        published = 0
        failed = 0
        skipped = 0

        for event in events:
            claim = self._repository.claim(event)

            if not claim.claimed:
                skipped += 1
                continue

            assert claim.item is not None
            assert claim.attempt_id is not None

            try:
                message_id = self._event_publisher.publish(
                    claim.item
                )
                self._repository.mark_delivered(
                    item=claim.item,
                    attempt_id=claim.attempt_id,
                    message_id=message_id,
                )
                published += 1
            except Exception as error:
                failed += 1
                self._repository.mark_failed_retryable(
                    item=claim.item,
                    attempt_id=claim.attempt_id,
                    error_message=str(error),
                )

        return PublishResult(
            examined=len(events),
            published=published,
            failed=failed,
            skipped=skipped,
        )
