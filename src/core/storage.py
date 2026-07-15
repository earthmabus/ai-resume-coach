from __future__ import annotations

from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from core.config import get_config
from core.keys import entity_gsi_pk


config = get_config()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(config.table_name)

s3 = boto3.client("s3")
document_bucket = config.document_bucket

sqs = boto3.client("sqs")
resume_analysis_queue_url = config.processing_queue_url


def is_conditional_failure(error: ClientError) -> bool:
    return (
        error.response.get("Error", {}).get("Code")
        == "ConditionalCheckFailedException"
    )


def put_item_if_absent(item: dict[str, Any]) -> bool:
    """
    Create an item only when the exact base-table key is not present.

    Returns True when the item was created and False when it already existed.
    """

    try:
        table.put_item(
            Item=item,
            ConditionExpression=(
                "attribute_not_exists(pk) AND attribute_not_exists(sk)"
            ),
        )
        return True
    except ClientError as error:
        if is_conditional_failure(error):
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
        IndexName="gsi1",
        KeyConditionExpression=Key("gsi1pk").eq(
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
