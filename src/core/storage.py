from __future__ import annotations

from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

from core.config import get_config
from core.dynamodb_contract import (
    GSI1_INDEX_NAME,
    GSI1_PARTITION_KEY,
)
from core.keys import entity_gsi_pk


config = get_config()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(config.table_name)
dynamodb_client = boto3.client("dynamodb")
serializer = TypeSerializer()

s3 = boto3.client("s3")
document_bucket = config.document_bucket

sqs = boto3.client("sqs")
resume_analysis_queue_url = config.processing_queue_url


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


def is_transaction_condition_failure(error: ClientError) -> bool:
    if (
        error.response.get("Error", {}).get("Code")
        != "TransactionCanceledException"
    ):
        return False

    reasons = error.response.get("CancellationReasons") or []

    if not reasons:
        return False

    return any(
        reason.get("Code") == "ConditionalCheckFailed"
        for reason in reasons
    )


def serialize_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        name: serializer.serialize(value)
        for name, value in item.items()
    }


def serialize_values(
    values: dict[str, Any],
) -> dict[str, Any]:
    return {
        name: serializer.serialize(value)
        for name, value in values.items()
    }


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


def put_items_and_outbox_if_absent(
    *,
    items: list[dict[str, Any]],
    outbox_item: dict[str, Any],
) -> bool:
    """
    Atomically create business records and their outbox record.

    Returns False when any target key already exists. Other transaction
    failures propagate so callers can mark the idempotency request retryable.
    """
    if not items:
        raise ValueError("at least one business item is required")

    normalized_items = [
        item_with_owner_region(item)
        for item in [*items, outbox_item]
    ]

    transact_items = [
        {
            "Put": {
                "TableName": config.table_name,
                "Item": serialize_item(item),
                "ConditionExpression": (
                    "attribute_not_exists(pk) "
                    "AND attribute_not_exists(sk)"
                ),
            }
        }
        for item in normalized_items
    ]

    try:
        dynamodb_client.transact_write_items(
            TransactItems=transact_items,
        )
        return True
    except ClientError as error:
        if is_transaction_condition_failure(error):
            return False

        raise


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
    Atomically update an existing business record and create an outbox event.

    Returns False when the business condition fails or the deterministic
    outbox event already exists. Other transaction failures propagate.
    """
    try:
        dynamodb_client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": config.table_name,
                        "Key": serialize_item(key),
                        "UpdateExpression": update_expression,
                        "ConditionExpression": condition_expression,
                        "ExpressionAttributeNames": (
                            expression_attribute_names
                        ),
                        "ExpressionAttributeValues": serialize_values(
                            expression_attribute_values
                        ),
                    }
                },
                {
                    "Put": {
                        "TableName": config.table_name,
                        "Item": serialize_item(outbox_item),
                        "ConditionExpression": (
                            "attribute_not_exists(pk) "
                            "AND attribute_not_exists(sk)"
                        ),
                    }
                },
            ],
        )
        return True
    except ClientError as error:
        if is_transaction_condition_failure(error):
            return False

        raise


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
