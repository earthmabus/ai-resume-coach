from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from botocore.exceptions import ClientError

from core.config import get_config
from core.errors import IdempotencyConflictError
from core.storage import (
    get_item_strong,
    is_conditional_failure,
    put_item_if_absent,
    table,
)


STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED_RETRYABLE = "FAILED_RETRYABLE"

DISPOSITION_RESERVED = "RESERVED"
DISPOSITION_REPLAY_COMPLETED = "REPLAY_COMPLETED"
DISPOSITION_REPLAY_IN_PROGRESS = "REPLAY_IN_PROGRESS"


@dataclass(frozen=True)
class IdempotencyReservation:
    disposition: str
    resource_id: str
    owner_region: str | None = None
    status_code: int | None = None
    response_body: dict[str, Any] | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def request_fingerprint(
    *,
    user_id: str,
    operation: str,
    body: dict[str, Any],
) -> str:
    return sha256_text(
        canonical_json(
            {
                "userId": user_id,
                "operation": operation,
                "body": body,
            }
        )
    )


def idempotency_key_hash(idempotency_key: str) -> str:
    return sha256_text(idempotency_key)


def idempotency_keys(
    *,
    user_id: str,
    operation: str,
    idempotency_key: str,
) -> tuple[str, str]:
    key_hash = idempotency_key_hash(idempotency_key)

    return (
        f"USER#{user_id}",
        f"IDEMPOTENCY#{operation}#{key_hash}",
    )


def _read_existing(
    *,
    pk: str,
    sk: str,
    request_hash: str,
) -> dict[str, Any]:
    existing = get_item_strong(pk, sk)

    if existing is None:
        raise RuntimeError(
            "Idempotency record exists but could not be read"
        )

    if existing.get("requestHash") != request_hash:
        raise IdempotencyConflictError()

    return existing


def _try_reacquire_retryable(
    *,
    pk: str,
    sk: str,
    request_hash: str,
    request_id: str,
    region: str,
) -> bool:
    try:
        table.update_item(
            Key={
                "pk": pk,
                "sk": sk,
            },
            UpdateExpression=(
                "SET #status = :inProgress, "
                "updatedAt = :updatedAt, "
                "updatedByRequestId = :requestId, "
                "lastUpdatedRegion = :region, "
"lastUpdatedByDeploymentId = :deploymentId, "
                "#version = #version + :one"
            ),
            ConditionExpression=(
                "#status = :failedRetryable "
                "AND requestHash = :requestHash"
            ),
            ExpressionAttributeNames={
                "#status": "status",
                "#version": "version",
            },
            ExpressionAttributeValues={
                ":inProgress": STATUS_IN_PROGRESS,
                ":failedRetryable": STATUS_FAILED_RETRYABLE,
                ":requestHash": request_hash,
                ":updatedAt": utc_now(),
                ":requestId": request_id,
                ":region": region,
                ":deploymentId": get_config().deployment_id,
                ":one": 1,
            },
        )

        return True
    except ClientError as error:
        if is_conditional_failure(error):
            return False

        raise


def reserve_request(
    *,
    user_id: str,
    operation: str,
    idempotency_key: str,
    request_hash: str,
    resource_id: str,
    request_id: str,
    region: str,
    owner_region: str | None = None,
    retention_days: int = 30,
) -> IdempotencyReservation:
    pk, sk = idempotency_keys(
        user_id=user_id,
        operation=operation,
        idempotency_key=idempotency_key,
    )

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    deployment_id = get_config().deployment_id
    normalized_owner_region = (
        str(owner_region or "").strip()
        or region
    )

    item = {
        "pk": pk,
        "sk": sk,
        "recordType": "idempotency",
        "userId": user_id,
        "operation": operation,
        "idempotencyKeyHash": idempotency_key_hash(idempotency_key),
        "requestHash": request_hash,
        "status": STATUS_IN_PROGRESS,
        "resourceId": resource_id,
        "createdByRequestId": request_id,
        "updatedByRequestId": request_id,
        "createdRegion": region,
        "ownerRegion": normalized_owner_region,
        "createdByDeploymentId": deployment_id,
        "lastUpdatedRegion": region,
        "lastUpdatedByDeploymentId": deployment_id,
        "createdAt": now_iso,
        "updatedAt": now_iso,
        "retentionUntil": (
            now + timedelta(days=retention_days)
        ).isoformat(),
        "version": 1,
    }

    if put_item_if_absent(item):
        return IdempotencyReservation(
            disposition=DISPOSITION_RESERVED,
            resource_id=resource_id,
            owner_region=normalized_owner_region,
        )

    existing = _read_existing(
        pk=pk,
        sk=sk,
        request_hash=request_hash,
    )

    existing_resource_id = str(existing["resourceId"])
    existing_status = existing.get("status")
    existing_owner_region = (
        str(
            existing.get("ownerRegion")
            or existing.get("createdRegion")
            or ""
        ).strip()
        or None
    )

    if existing_status == STATUS_COMPLETED:
        return IdempotencyReservation(
            disposition=DISPOSITION_REPLAY_COMPLETED,
            resource_id=existing_resource_id,
            owner_region=existing_owner_region,
            status_code=int(existing["responseStatusCode"]),
            response_body=existing.get("responseBody") or {},
        )

    if existing_status == STATUS_FAILED_RETRYABLE:
        acquired = _try_reacquire_retryable(
            pk=pk,
            sk=sk,
            request_hash=request_hash,
            request_id=request_id,
            region=region,
        )

        if acquired:
            return IdempotencyReservation(
                disposition=DISPOSITION_RESERVED,
                resource_id=existing_resource_id,
                owner_region=existing_owner_region,
            )

        existing = _read_existing(
            pk=pk,
            sk=sk,
            request_hash=request_hash,
        )

        if existing.get("status") == STATUS_COMPLETED:
            return IdempotencyReservation(
                disposition=DISPOSITION_REPLAY_COMPLETED,
                resource_id=existing_resource_id,
                owner_region=(
                    str(
                        existing.get("ownerRegion")
                        or existing.get("createdRegion")
                        or ""
                    ).strip()
                    or None
                ),
                status_code=int(existing["responseStatusCode"]),
                response_body=existing.get("responseBody") or {},
            )

    return IdempotencyReservation(
        disposition=DISPOSITION_REPLAY_IN_PROGRESS,
        resource_id=existing_resource_id,
        owner_region=existing_owner_region,
        status_code=int(existing.get("responseStatusCode", 202)),
        response_body=existing.get("responseBody"),
    )


def complete_request(
    *,
    user_id: str,
    operation: str,
    idempotency_key: str,
    request_hash: str,
    resource_id: str,
    request_id: str,
    region: str,
    status_code: int,
    response_body: dict[str, Any],
) -> None:
    pk, sk = idempotency_keys(
        user_id=user_id,
        operation=operation,
        idempotency_key=idempotency_key,
    )

    now = utc_now()

    try:
        table.update_item(
            Key={
                "pk": pk,
                "sk": sk,
            },
            UpdateExpression=(
                "SET #status = :completed, "
                "responseStatusCode = :responseStatusCode, "
                "responseBody = :responseBody, "
                "completedAt = :completedAt, "
                "updatedAt = :updatedAt, "
                "updatedByRequestId = :requestId, "
                "lastUpdatedRegion = :region, "
"lastUpdatedByDeploymentId = :deploymentId, "
                "#version = #version + :one"
            ),
            ConditionExpression=(
                "#status = :inProgress "
                "AND requestHash = :requestHash "
                "AND resourceId = :resourceId"
            ),
            ExpressionAttributeNames={
                "#status": "status",
                "#version": "version",
            },
            ExpressionAttributeValues={
                ":completed": STATUS_COMPLETED,
                ":inProgress": STATUS_IN_PROGRESS,
                ":requestHash": request_hash,
                ":resourceId": resource_id,
                ":responseStatusCode": status_code,
                ":responseBody": response_body,
                ":completedAt": now,
                ":updatedAt": now,
                ":requestId": request_id,
                ":region": region,
                ":deploymentId": get_config().deployment_id,
                ":one": 1,
            },
        )
    except ClientError as error:
        if is_conditional_failure(error):
            existing = get_item_strong(pk, sk)

            if (
                existing
                and existing.get("status") == STATUS_COMPLETED
                and existing.get("requestHash") == request_hash
                and existing.get("resourceId") == resource_id
            ):
                return

        raise


def mark_request_retryable(
    *,
    user_id: str,
    operation: str,
    idempotency_key: str,
    request_hash: str,
    resource_id: str,
    request_id: str,
    region: str,
) -> None:
    pk, sk = idempotency_keys(
        user_id=user_id,
        operation=operation,
        idempotency_key=idempotency_key,
    )

    now = utc_now()

    try:
        table.update_item(
            Key={
                "pk": pk,
                "sk": sk,
            },
            UpdateExpression=(
                "SET #status = :failedRetryable, "
                "updatedAt = :updatedAt, "
                "updatedByRequestId = :requestId, "
                "lastUpdatedRegion = :region, "
"lastUpdatedByDeploymentId = :deploymentId, "
                "#version = #version + :one"
            ),
            ConditionExpression=(
                "#status = :inProgress "
                "AND requestHash = :requestHash "
                "AND resourceId = :resourceId"
            ),
            ExpressionAttributeNames={
                "#status": "status",
                "#version": "version",
            },
            ExpressionAttributeValues={
                ":failedRetryable": STATUS_FAILED_RETRYABLE,
                ":inProgress": STATUS_IN_PROGRESS,
                ":requestHash": request_hash,
                ":resourceId": resource_id,
                ":updatedAt": now,
                ":requestId": request_id,
                ":region": region,
                ":deploymentId": get_config().deployment_id,
                ":one": 1,
            },
        )
    except ClientError as error:
        if is_conditional_failure(error):
            return

        raise
