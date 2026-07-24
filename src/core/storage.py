from __future__ import annotations

from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from core.config import get_config
from core.dynamodb_contract import (
    GSI1_INDEX_NAME,
    GSI1_PARTITION_KEY,
    GSI1_SORT_KEY,
)
from core.keys import entity_gsi_pk, outbox_status_pk, outbox_status_sk
from core.outbox import (
    OUTBOX_STATUS_DELIVERED,
    OUTBOX_STATUS_DISPATCHING,
    OUTBOX_STATUS_FAILED_PERMANENT,
    OUTBOX_STATUS_FAILED_RETRYABLE,
    OUTBOX_STATUS_PENDING,
    OUTBOX_STATUS_PREPARING,
)


config = get_config()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(config.table_name)

s3 = boto3.client("s3")
document_bucket = config.document_bucket

sqs = boto3.client("sqs")
resume_analysis_queue_url = config.processing_queue_url


ACTIVE_OUTBOX_STATUSES = {
    OUTBOX_STATUS_PENDING,
    OUTBOX_STATUS_DISPATCHING,
    OUTBOX_STATUS_DELIVERED,
    OUTBOX_STATUS_FAILED_RETRYABLE,
    OUTBOX_STATUS_FAILED_PERMANENT,
}


def item_with_owner_region(
    item: dict[str, Any],
) -> dict[str, Any]:
    if item.get("ownerRegion"):
        return item

    owner_region = str(
        item.get("createdRegion") or ""
    ).strip()

    if not owner_region:
        return item

    return {
        **item,
        "ownerRegion": owner_region,
    }


def is_conditional_failure(error: ClientError) -> bool:
    return (
        error.response.get("Error", {}).get("Code")
        == "ConditionalCheckFailedException"
    )


def _get_item_by_key(
    item: dict[str, Any],
) -> dict[str, Any] | None:
    return get_item_strong(
        str(item["pk"]),
        str(item["sk"]),
    )


def _same_creation(existing: dict[str, Any], expected: dict[str, Any]) -> bool:
    expected_hash = str(
        expected.get("createdByRequestHash") or ""
    ).strip()
    existing_hash = str(
        existing.get("createdByRequestHash") or ""
    ).strip()

    if expected_hash and existing_hash:
        return expected_hash == existing_hash

    expected_request_id = str(
        expected.get("createdByRequestId") or ""
    ).strip()
    existing_request_id = str(
        existing.get("createdByRequestId") or ""
    ).strip()

    return bool(
        expected_request_id
        and existing_request_id == expected_request_id
    )


def _same_outbox_event(
    existing: dict[str, Any],
    expected: dict[str, Any],
) -> bool:
    return (
        existing.get("recordType") == "outboxEvent"
        and existing.get("eventId") == expected.get("eventId")
        and existing.get("payloadHash") == expected.get("payloadHash")
        and _same_creation(existing, expected)
    )


def put_item_if_absent(item: dict[str, Any]) -> bool:
    """
    Create an item only when the exact base-table key is not present.

    Returns True when the item was created and False when it already existed.
    """

    try:
        table.put_item(
            Item=item_with_owner_region(item),
            ConditionExpression=(
                "attribute_not_exists(pk) AND attribute_not_exists(sk)"
            ),
        )
        return True
    except ClientError as error:
        if is_conditional_failure(error):
            return False

        raise


def _preparing_outbox_item(
    outbox_item: dict[str, Any],
) -> dict[str, Any]:
    prepared = item_with_owner_region(dict(outbox_item))
    prepared["status"] = OUTBOX_STATUS_PREPARING
    prepared.pop(GSI1_PARTITION_KEY, None)
    prepared.pop(GSI1_SORT_KEY, None)
    return prepared


def _ensure_outbox_prepared(
    outbox_item: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    prepared = _preparing_outbox_item(outbox_item)

    try:
        table.put_item(
            Item=prepared,
            ConditionExpression=(
                "attribute_not_exists(pk) AND attribute_not_exists(sk)"
            ),
        )
        return prepared, True
    except ClientError as error:
        if not is_conditional_failure(error):
            raise

    existing = _get_item_by_key(prepared)
    if not existing or not _same_outbox_event(existing, prepared):
        return prepared, False

    return existing, True


def _ensure_business_item(
    item: dict[str, Any],
) -> bool:
    normalized = item_with_owner_region(item)

    try:
        table.put_item(
            Item=normalized,
            ConditionExpression=(
                "attribute_not_exists(pk) AND attribute_not_exists(sk)"
            ),
        )
        return True
    except ClientError as error:
        if not is_conditional_failure(error):
            raise

    existing = _get_item_by_key(normalized)
    return bool(
        existing
        and existing.get("recordType") == normalized.get("recordType")
        and _same_creation(existing, normalized)
    )


def _activate_outbox(
    outbox_item: dict[str, Any],
) -> bool:
    expected = item_with_owner_region(outbox_item)
    event_id = str(expected["eventId"])
    created_at = str(expected["createdAt"])

    try:
        table.update_item(
            Key={
                "pk": expected["pk"],
                "sk": expected["sk"],
            },
            UpdateExpression=(
                "SET #status = :pending, "
                "#gsi1pk = :gsi1pk, "
                "#gsi1sk = :gsi1sk, "
                "updatedAt = :updatedAt"
            ),
            ConditionExpression=(
                "#status = :preparing AND payloadHash = :payloadHash"
            ),
            ExpressionAttributeNames={
                "#status": "status",
                "#gsi1pk": GSI1_PARTITION_KEY,
                "#gsi1sk": GSI1_SORT_KEY,
            },
            ExpressionAttributeValues={
                ":preparing": OUTBOX_STATUS_PREPARING,
                ":pending": OUTBOX_STATUS_PENDING,
                ":payloadHash": expected["payloadHash"],
                ":gsi1pk": outbox_status_pk(OUTBOX_STATUS_PENDING),
                ":gsi1sk": outbox_status_sk(
                    created_at=created_at,
                    event_id=event_id,
                ),
                ":updatedAt": expected.get("updatedAt", created_at),
            },
        )
        return True
    except ClientError as error:
        if not is_conditional_failure(error):
            raise

    existing = _get_item_by_key(expected)
    return bool(
        existing
        and _same_outbox_event(existing, expected)
        and existing.get("status") in ACTIVE_OUTBOX_STATUSES
    )


def put_items_and_outbox_if_absent(
    *,
    items: list[dict[str, Any]],
    outbox_item: dict[str, Any],
) -> bool:
    """
    Idempotently create business records and activate their outbox event.

    DynamoDB strongly consistent multi-Region global tables do not support
    transaction APIs. This routine therefore uses a recoverable three-stage
    protocol:

    1. Create a deterministic, non-dispatchable PREPARING outbox record.
    2. Conditionally create every deterministic business record.
    3. Activate the outbox record by moving it to PENDING and adding its
       sparse-GSI keys.

    A retry can safely resume after any stage. Existing records are accepted
    only when they were created by the same logical request. The publisher
    cannot observe the outbox record until all business records are present.
    """
    if not items:
        raise ValueError("at least one business item is required")

    _, prepared = _ensure_outbox_prepared(outbox_item)
    if not prepared:
        return False

    for item in items:
        if not _ensure_business_item(item):
            return False

    return _activate_outbox(outbox_item)


def put_item_and_outbox_if_absent(
    *,
    item: dict[str, Any],
    outbox_item: dict[str, Any],
) -> bool:
    return put_items_and_outbox_if_absent(
        items=[item],
        outbox_item=outbox_item,
    )


def update_item_and_put_outbox(
    *,
    key: dict[str, Any],
    update_expression: str,
    condition_expression: str,
    expression_attribute_names: dict[str, str],
    expression_attribute_values: dict[str, Any],
    outbox_item: dict[str, Any],
) -> bool:
    """
    Idempotently update a record and activate a deterministic outbox event.

    The outbox begins in PREPARING without sparse-GSI keys. After the
    conditional business update succeeds, the outbox is activated to PENDING.
    If a prior attempt completed the business update but stopped before
    activation, a retry recognizes the same updatedByRequestId and finishes
    activating the event.
    """
    _, prepared = _ensure_outbox_prepared(outbox_item)
    if not prepared:
        return False

    try:
        table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ConditionExpression=condition_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
        )
    except ClientError as error:
        if not is_conditional_failure(error):
            raise

        existing = get_item_strong(
            str(key["pk"]),
            str(key["sk"]),
        )
        request_id = str(
            outbox_item.get("createdByRequestId") or ""
        ).strip()

        if not existing or existing.get("updatedByRequestId") != request_id:
            return False

    return _activate_outbox(outbox_item)


def get_item_strong(
    pk: str,
    sk: str,
) -> dict[str, Any] | None:
    response = table.get_item(
        Key={
            "pk": pk,
            "sk": sk,
        },
        ConsistentRead=True,
    )

    return response.get("Item")


def update_item_conditionally(
    *,
    pk: str,
    sk: str,
    update_expression: str,
    condition_expression: str,
    expression_attribute_names: dict[str, str] | None = None,
    expression_attribute_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parameters: dict[str, Any] = {
        "Key": {
            "pk": pk,
            "sk": sk,
        },
        "UpdateExpression": update_expression,
        "ConditionExpression": condition_expression,
        "ReturnValues": "ALL_NEW",
    }

    if expression_attribute_names:
        parameters["ExpressionAttributeNames"] = (
            expression_attribute_names
        )

    if expression_attribute_values:
        parameters["ExpressionAttributeValues"] = (
            expression_attribute_values
        )

    response = table.update_item(**parameters)

    return response["Attributes"]


def get_entity_by_id(
    entity_id: str,
    expected_record_type: str | None = None,
) -> dict[str, Any] | None:
    """
    Retrieve an entity through gsi1.

    This remains suitable for display reads, but must not be used as the
    authoritative read for concurrency or idempotency decisions.
    """

    response = table.query(
        IndexName=GSI1_INDEX_NAME,
        KeyConditionExpression=Key(GSI1_PARTITION_KEY).eq(
            entity_gsi_pk(entity_id)
        ),
    )

    items = response.get("Items", [])

    if expected_record_type:
        items = [
            item
            for item in items
            if item.get("recordType") == expected_record_type
        ]

    return items[0] if items else None
