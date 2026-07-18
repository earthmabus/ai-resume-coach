from __future__ import annotations

import json
import time
import uuid
from concurrent.futures import (
    Future,
    ThreadPoolExecutor,
    as_completed,
)
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from core.keys import outbox_status_pk
from core.outbox import (
    OUTBOX_STATUS_DELIVERED,
    OUTBOX_STATUS_DISPATCHING,
    OUTBOX_STATUS_FAILED_RETRYABLE,
    OUTBOX_STATUS_FAILED_PERMANENT,
    OUTBOX_STATUS_PENDING,
)


DEFAULT_DISPATCH_LEASE_SECONDS = 300
DEFAULT_BATCH_SIZE = 25
DEFAULT_MAX_WORKERS = 4
DEFAULT_MAX_DELIVERY_ATTEMPTS = 20
DEFAULT_DELIVERED_RETENTION_SECONDS = 30 * 24 * 60 * 60
MAX_ERROR_MESSAGE_LENGTH = 2000
MAX_QUERY_PAGES_PER_STATUS = 10

RETRY_DELAY_SECONDS_BY_ATTEMPT = {
    1: 60,
    2: 120,
    3: 240,
    4: 480,
    5: 900,
}
MAX_RETRY_DELAY_SECONDS = 1800


@dataclass(frozen=True)
class PublishResult:
    examined: int = 0
    claimed: int = 0
    published: int = 0
    failed: int = 0
    skipped: int = 0
    permanently_failed: int = 0


@dataclass(frozen=True)
class ClaimResult:
    claimed: bool
    item: dict[str, Any] | None = None
    attempt_id: str | None = None


@dataclass(frozen=True)
class ClaimedEvent:
    item: dict[str, Any]
    attempt_id: str


@dataclass(frozen=True)
class ClaimedEventResult:
    published: bool
    permanently_failed: bool = False


def retry_delay_seconds(delivery_attempts: int) -> int:
    """Return the retry delay for the completed delivery attempt."""
    normalized_attempts = max(int(delivery_attempts), 1)

    return RETRY_DELAY_SECONDS_BY_ATTEMPT.get(
        normalized_attempts,
        MAX_RETRY_DELAY_SECONDS,
    )


def json_compatible(value: Any) -> Any:
    """Convert DynamoDB values into JSON-compatible Python values."""
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)

        return float(value)

    if isinstance(value, dict):
        return {
            key: json_compatible(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            json_compatible(item)
            for item in value
        ]

    if isinstance(value, set):
        return [
            json_compatible(item)
            for item in value
        ]

    return value


class DynamoDbOutboxRepository:
    """Persistence operations for dispatchable outbox records."""

    def __init__(
        self,
        *,
        table: Any,
        region: str,
        deployment_id: str = "unknown",
        lease_seconds: int = DEFAULT_DISPATCH_LEASE_SECONDS,
        delivered_retention_seconds: int = DEFAULT_DELIVERED_RETENTION_SECONDS,
        now: Callable[[], datetime] | None = None,
        epoch_seconds: Callable[[], int] | None = None,
    ) -> None:
        if lease_seconds <= 0:
            raise ValueError(
                "lease_seconds must be greater than zero"
            )

        if delivered_retention_seconds <= 0:
            raise ValueError(
                "delivered_retention_seconds must be greater than zero"
            )

        self._table = table
        self._region = (
            str(region or "").strip()
            or "unknown"
        )
        self._deployment_id = (
            str(deployment_id or "").strip()
            or "unknown"
        )
        self._lease_seconds = lease_seconds
        self._delivered_retention_seconds = delivered_retention_seconds
        self._now = (
            now
            or (
                lambda: datetime.now(
                    timezone.utc
                )
            )
        )
        self._epoch_seconds = (
            epoch_seconds
            or (
                lambda: int(time.time())
            )
        )

    def list_dispatchable(
        self,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        """
        Return a bounded set of records eligible for an attempt.

        PENDING records are immediately eligible. FAILED_RETRYABLE records
        are eligible only after nextDeliveryAttemptAt. A missing retry time
        remains immediately eligible for compatibility with older records.
        DISPATCHING records are eligible only after their lease expires.
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
            self._append_eligible_status_items(
                results=results,
                status=status,
                limit=limit,
                now_epoch=now_epoch,
            )

            if len(results) >= limit:
                break

        return results

    def _append_eligible_status_items(
        self,
        *,
        results: list[dict[str, Any]],
        status: str,
        limit: int,
        now_epoch: int,
    ) -> None:
        last_evaluated_key: (
            dict[str, Any] | None
        ) = None
        pages_read = 0

        while len(results) < limit:
            parameters: dict[str, Any] = {
                "IndexName": "gsi1",
                "KeyConditionExpression": (
                    Key("gsi1pk").eq(
                        outbox_status_pk(status)
                    )
                ),
                "Limit": limit - len(results),
                "ScanIndexForward": True,
            }

            if last_evaluated_key is not None:
                parameters[
                    "ExclusiveStartKey"
                ] = last_evaluated_key

            response = self._table.query(
                **parameters
            )
            pages_read += 1

            for item in response.get(
                "Items",
                [],
            ):
                if self._is_dispatchable(
                    item=item,
                    status=status,
                    now_epoch=now_epoch,
                ):
                    results.append(item)

                    if len(results) >= limit:
                        break

            last_evaluated_key = response.get(
                "LastEvaluatedKey"
            )

            if (
                not last_evaluated_key
                or pages_read
                >= MAX_QUERY_PAGES_PER_STATUS
            ):
                break

    @staticmethod
    def _is_dispatchable(
        *,
        item: dict[str, Any],
        status: str,
        now_epoch: int,
    ) -> bool:
        if status == OUTBOX_STATUS_FAILED_RETRYABLE:
            return int(
                item.get(
                    "nextDeliveryAttemptAt",
                    0,
                )
            ) <= now_epoch

        if status == OUTBOX_STATUS_DISPATCHING:
            return int(
                item.get(
                    "dispatchLeaseExpiresAt",
                    0,
                )
            ) <= now_epoch

        return True

    def claim(
        self,
        item: dict[str, Any],
    ) -> ClaimResult:
        event_id = str(
            item.get("eventId") or ""
        ).strip()
        current_status = str(
            item.get("status") or ""
        ).strip()
        current_version = int(
            item.get("version", 0)
        )

        if not event_id:
            raise ValueError(
                "outbox eventId is required"
            )

        if current_status not in {
            OUTBOX_STATUS_PENDING,
            OUTBOX_STATUS_FAILED_RETRYABLE,
            OUTBOX_STATUS_DISPATCHING,
        }:
            return ClaimResult(
                claimed=False
            )

        attempt_id = str(uuid.uuid4())
        now = self._now().isoformat()
        now_epoch = self._epoch_seconds()
        lease_expires_at = (
            now_epoch
            + self._lease_seconds
        )

        condition_expression = (
            "#status = :expectedStatus "
            "AND ("
            "#version = :expectedVersion "
            "OR (attribute_not_exists(#version) "
            "AND :expectedVersion = :zero)"
            ")"
        )

        values: dict[str, Any] = {
            ":dispatching": (
                OUTBOX_STATUS_DISPATCHING
            ),
            ":dispatchingPk": (
                outbox_status_pk(
                    OUTBOX_STATUS_DISPATCHING
                )
            ),
            ":attemptId": attempt_id,
            ":now": now,
            ":leaseExpiresAt": (
                lease_expires_at
            ),
            ":region": self._region,
            ":deploymentId": self._deployment_id,
            ":expectedStatus": (
                current_status
            ),
            ":expectedVersion": (
                current_version
            ),
            ":zero": 0,
            ":one": 1,
        }

        if (
            current_status
            == OUTBOX_STATUS_FAILED_RETRYABLE
        ):
            condition_expression += (
                " AND ("
                "attribute_not_exists("
                "nextDeliveryAttemptAt"
                ") "
                "OR nextDeliveryAttemptAt "
                "<= :nowEpoch"
                ")"
            )
            values[":nowEpoch"] = now_epoch

        if (
            current_status
            == OUTBOX_STATUS_DISPATCHING
        ):
            condition_expression += (
                " AND dispatchLeaseExpiresAt "
                "<= :nowEpoch"
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
                    "dispatchLeaseExpiresAt = "
                    ":leaseExpiresAt, "
                    "updatedAt = :now, "
                    "updatedByRequestId = :attemptId, "
                    "lastUpdatedRegion = :region, "
"lastUpdatedByDeploymentId = :deploymentId, "
                    "deliveryAttempts = "
                    "if_not_exists("
                    "deliveryAttempts, :zero"
                    ") + :one, "
                    "#version = if_not_exists("
                    "#version, :zero"
                    ") + :one "
                    "REMOVE nextDeliveryAttemptAt"
                ),
                ConditionExpression=(
                    condition_expression
                ),
                ExpressionAttributeNames={
                    "#status": "status",
                    "#version": "version",
                },
                ExpressionAttributeValues=(
                    values
                ),
                ReturnValues="ALL_NEW",
            )
        except ClientError as error:
            if self._is_conditional_failure(
                error
            ):
                return ClaimResult(
                    claimed=False
                )

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
        expires_at = (
            self._epoch_seconds()
            + self._delivered_retention_seconds
        )

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
"lastUpdatedByDeploymentId = :deploymentId, "
                "transportMessageId = :messageId, "
                "expiresAt = :expiresAt, "
                "#version = if_not_exists("
                "#version, :zero"
                ") + :one "
                "REMOVE gsi1pk, gsi1sk, "
                "dispatchAttemptId, "
                "dispatchStartedAt, "
                "dispatchLeaseExpiresAt, "
                "nextDeliveryAttemptAt, "
                "lastDeliveryError, "
                "lastDeliveryFailedAt"
            ),
            ConditionExpression=(
                "#status = :dispatching "
                "AND dispatchAttemptId = "
                ":attemptId"
            ),
            ExpressionAttributeNames={
                "#status": "status",
                "#version": "version",
            },
            ExpressionAttributeValues={
                ":delivered": (
                    OUTBOX_STATUS_DELIVERED
                ),
                ":dispatching": (
                    OUTBOX_STATUS_DISPATCHING
                ),
                ":attemptId": attempt_id,
                ":messageId": message_id,
                ":expiresAt": expires_at,
                ":now": now,
                ":region": self._region,
            ":deploymentId": self._deployment_id,
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
        now_epoch = self._epoch_seconds()
        delivery_attempts = max(
            int(
                item.get(
                    "deliveryAttempts",
                    1,
                )
            ),
            1,
        )
        next_attempt_at = (
            now_epoch
            + retry_delay_seconds(
                delivery_attempts
            )
        )
        truncated_error = str(
            error_message or ""
        )[:MAX_ERROR_MESSAGE_LENGTH]

        try:
            response = self._table.update_item(
                Key={
                    "pk": item["pk"],
                    "sk": item["sk"],
                },
                UpdateExpression=(
                    "SET #status = "
                    ":failedRetryable, "
                    "gsi1pk = "
                    ":failedRetryablePk, "
                    "nextDeliveryAttemptAt = "
                    ":nextAttemptAt, "
                    "lastDeliveryError = "
                    ":errorMessage, "
                    "lastDeliveryFailedAt = :now, "
                    "updatedAt = :now, "
                    "updatedByRequestId = "
                    ":attemptId, "
                    "lastUpdatedRegion = :region, "
"lastUpdatedByDeploymentId = :deploymentId, "
                    "#version = if_not_exists("
                    "#version, :zero"
                    ") + :one "
                    "REMOVE dispatchAttemptId, "
                    "dispatchStartedAt, "
                    "dispatchLeaseExpiresAt"
                ),
                ConditionExpression=(
                    "#status = :dispatching "
                    "AND dispatchAttemptId = "
                    ":attemptId"
                ),
                ExpressionAttributeNames={
                    "#status": "status",
                    "#version": "version",
                },
                ExpressionAttributeValues={
                    ":failedRetryable": (
                        OUTBOX_STATUS_FAILED_RETRYABLE
                    ),
                    ":failedRetryablePk": (
                        outbox_status_pk(
                            OUTBOX_STATUS_FAILED_RETRYABLE
                        )
                    ),
                    ":dispatching": (
                        OUTBOX_STATUS_DISPATCHING
                    ),
                    ":attemptId": attempt_id,
                    ":nextAttemptAt": (
                        next_attempt_at
                    ),
                    ":errorMessage": (
                        truncated_error
                    ),
                    ":now": now,
                    ":region": self._region,
            ":deploymentId": self._deployment_id,
                    ":zero": 0,
                    ":one": 1,
                },
                ReturnValues="ALL_NEW",
            )
        except ClientError as error:
            if self._is_conditional_failure(
                error
            ):
                return None

            raise

        return response["Attributes"]

    def mark_failed_permanent(
        self,
        *,
        item: dict[str, Any],
        attempt_id: str,
        error_message: str,
    ) -> dict[str, Any] | None:
        now = self._now().isoformat()
        truncated_error = str(
            error_message or ""
        )[:MAX_ERROR_MESSAGE_LENGTH]

        try:
            response = self._table.update_item(
                Key={
                    "pk": item["pk"],
                    "sk": item["sk"],
                },
                UpdateExpression=(
                    "SET #status = :failedPermanent, "
                    "permanentlyFailedAt = :now, "
                    "lastDeliveryError = :errorMessage, "
                    "lastDeliveryFailedAt = :now, "
                    "updatedAt = :now, "
                    "updatedByRequestId = :attemptId, "
                    "lastUpdatedRegion = :region, "
"lastUpdatedByDeploymentId = :deploymentId, "
                    "#version = if_not_exists("
                    "#version, :zero"
                    ") + :one "
                    "REMOVE gsi1pk, gsi1sk, "
                    "dispatchAttemptId, "
                    "dispatchStartedAt, "
                    "dispatchLeaseExpiresAt, "
                    "nextDeliveryAttemptAt, expiresAt"
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
                    ":failedPermanent": (
                        OUTBOX_STATUS_FAILED_PERMANENT
                    ),
                    ":dispatching": (
                        OUTBOX_STATUS_DISPATCHING
                    ),
                    ":attemptId": attempt_id,
                    ":errorMessage": truncated_error,
                    ":now": now,
                    ":region": self._region,
            ":deploymentId": self._deployment_id,
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
    def _is_conditional_failure(
        error: ClientError,
    ) -> bool:
        return (
            error.response.get(
                "Error",
                {},
            ).get("Code")
            == (
                "ConditionalCheckFailedException"
            )
        )


class SqsEventPublisher:
    """Publish outbox payloads to the existing worker queue."""

    def __init__(
        self,
        *,
        client: Any,
        queue_url: str,
    ) -> None:
        normalized_queue_url = str(
            queue_url or ""
        ).strip()

        if not normalized_queue_url:
            raise ValueError(
                "queue_url is required"
            )

        self._client = client
        self._queue_url = (
            normalized_queue_url
        )

    def publish(
        self,
        item: dict[str, Any],
    ) -> str:
        payload = item.get("payload")

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "outbox payload must be "
                "a dictionary"
            )

        message = json_compatible(
            {
                **payload,
                "outboxEventId": (
                    item["eventId"]
                ),
                "eventType": (
                    item["eventType"]
                ),
                "eventVersion": (
                    item["eventVersion"]
                ),
                "requestId": item.get(
                    "createdByRequestId",
                    "",
                ),
                "submittedAt": item.get(
                    "createdAt",
                    "",
                ),
                "sourceRegion": item.get(
                    "createdRegion",
                    payload.get("sourceRegion", ""),
                ),
                "ownerRegion": item.get(
                    "ownerRegion",
                    payload.get("ownerRegion", ""),
                ),
                "sourceDeploymentId": item.get(
                    "createdByDeploymentId",
                    payload.get("sourceDeploymentId", ""),
                ),
            }
        )

        response = self._client.send_message(
            QueueUrl=self._queue_url,
            MessageBody=json.dumps(
                message,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
        )

        message_id = str(
            response.get("MessageId") or ""
        ).strip()

        if not message_id:
            raise RuntimeError(
                "SQS did not return a MessageId"
            )

        return message_id


class OutboxPublisher:
    """
    Coordinate discovery, serial claims, and parallel delivery.

    Claiming remains serial so DynamoDB continues to be the single
    ownership boundary. Only the already-claimed publish and status-update
    lifecycle runs concurrently.
    """

    def __init__(
        self,
        *,
        repository: DynamoDbOutboxRepository,
        event_publisher: SqsEventPublisher,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_workers: int = DEFAULT_MAX_WORKERS,
        max_delivery_attempts: int = DEFAULT_MAX_DELIVERY_ATTEMPTS,
    ) -> None:
        if batch_size <= 0:
            raise ValueError(
                "batch_size must be greater than zero"
            )

        if max_workers <= 0:
            raise ValueError(
                "max_workers must be greater than zero"
            )

        if max_delivery_attempts <= 0:
            raise ValueError(
                "max_delivery_attempts must be greater than zero"
            )

        self._repository = repository
        self._event_publisher = (
            event_publisher
        )
        self._batch_size = batch_size
        self._max_workers = max_workers
        self._max_delivery_attempts = max_delivery_attempts

    def _publish_claimed_event(
        self,
        claimed_event: ClaimedEvent,
    ) -> ClaimedEventResult:
        try:
            message_id = (
                self._event_publisher.publish(
                    claimed_event.item
                )
            )

            self._repository.mark_delivered(
                item=claimed_event.item,
                attempt_id=(
                    claimed_event.attempt_id
                ),
                message_id=message_id,
            )

            return ClaimedEventResult(
                published=True
            )

        except Exception as error:
            delivery_attempts = max(
                int(
                    claimed_event.item.get(
                        "deliveryAttempts",
                        1,
                    )
                ),
                1,
            )

            if delivery_attempts >= self._max_delivery_attempts:
                self._repository.mark_failed_permanent(
                    item=claimed_event.item,
                    attempt_id=claimed_event.attempt_id,
                    error_message=str(error),
                )

                return ClaimedEventResult(
                    published=False,
                    permanently_failed=True,
                )

            self._repository.mark_failed_retryable(
                item=claimed_event.item,
                attempt_id=claimed_event.attempt_id,
                error_message=str(error),
            )

            return ClaimedEventResult(
                published=False
            )

    def publish_pending(
        self,
    ) -> PublishResult:
        events = (
            self._repository.list_dispatchable(
                limit=self._batch_size,
            )
        )

        claimed_events: list[
            ClaimedEvent
        ] = []
        skipped = 0

        for event in events:
            claim = self._repository.claim(
                event
            )

            if not claim.claimed:
                skipped += 1
                continue

            assert claim.item is not None
            assert claim.attempt_id is not None

            claimed_events.append(
                ClaimedEvent(
                    item=claim.item,
                    attempt_id=(
                        claim.attempt_id
                    ),
                )
            )

        published = 0
        failed = 0
        permanently_failed = 0

        if claimed_events:
            worker_count = min(
                self._max_workers,
                len(claimed_events),
            )

            with ThreadPoolExecutor(
                max_workers=worker_count,
                thread_name_prefix=(
                    "outbox-publisher"
                ),
            ) as executor:
                futures: list[
                    Future[ClaimedEventResult]
                ] = [
                    executor.submit(
                        self._publish_claimed_event,
                        claimed_event,
                    )
                    for claimed_event
                    in claimed_events
                ]

                for future in as_completed(
                    futures
                ):
                    result = future.result()

                    if result.published:
                        published += 1
                    else:
                        failed += 1

                        if result.permanently_failed:
                            permanently_failed += 1

        return PublishResult(
            examined=len(events),
            claimed=len(claimed_events),
            published=published,
            failed=failed,
            skipped=skipped,
            permanently_failed=permanently_failed,
        )
