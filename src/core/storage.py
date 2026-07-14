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


#def get_entity_by_id(entity_id, expected_record_type=None):
#    response = table.query(
#        IndexName="gsi1",
#        KeyConditionExpression=Key("gsi1pk").eq(
#            entity_gsi_pk(entity_id)
#        ),
#    )
#
#    items = response.get("Items", [])
#
#    if expected_record_type:
#        items = [
#            item
#            for item in items
#            if item.get("recordType") == expected_record_type
#        ]
#
#    return items[0] if items else None


def is_conditional_failure(exc: ClientError) -> bool:
    return (
        exc.response.get("Error", {}).get("Code")
        == "ConditionalCheckFailedException"
    )


def put_item_if_absent(item: dict) -> bool:
    try:
        table.put_item(
            Item=item,
            ConditionExpression=(
                "attribute_not_exists(pk) AND attribute_not_exists(sk)"
            ),
        )
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def get_item_strong(pk: str, sk: str) -> dict | None:
    response = table.get_item(
        Key={"pk": pk, "sk": sk},
        ConsistentRead=True,
    )
    return response.get("Item")


def update_item_with_version(
    *,
    pk: str,
    sk: str,
    expected_version: int,
    update_expression: str,
    expression_names: dict,
    expression_values: dict,
) -> dict:
    values = {
        **expression_values,
        ":expectedVersion": expected_version,
        ":nextVersion": expected_version + 1,
    }

    response = table.update_item(
        Key={"pk": pk, "sk": sk},
        UpdateExpression=(
            f"{update_expression}, "
            "#version = :nextVersion"
        ),
        ConditionExpression=(
            "attribute_exists(pk) "
            "AND attribute_exists(sk) "
            "AND #version = :expectedVersion"
        ),
        ExpressionAttributeNames={
            **expression_names,
            "#version": "version",
        },
        ExpressionAttributeValues=values,
        ReturnValues="ALL_NEW",
    )

    return response["Attributes"]


def update_item_conditionally(
    *,
    pk: str,
    sk: str,
    update_expression: str,
    condition_expression: str,
    expression_attribute_names: dict[str, str] | None = None,
    expression_attribute_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = table.update_item(
        Key={
            "pk": pk,
            "sk": sk,
        },
        UpdateExpression=update_expression,
        ConditionExpression=condition_expression,
        ExpressionAttributeNames=expression_attribute_names or {},
        ExpressionAttributeValues=expression_attribute_values or {},
        ReturnValues="ALL_NEW",
    )

    return response["Attributes"]


def delete_item_with_version(
    *,
    pk: str,
    sk: str,
    expected_version: int,
    user_id: str,
) -> dict | None:
    response = table.delete_item(
        Key={"pk": pk, "sk": sk},
        ConditionExpression=(
            "attribute_exists(pk) "
            "AND attribute_exists(sk) "
            "AND userId = :userId "
            "AND #version = :expectedVersion"
        ),
        ExpressionAttributeNames={
            "#version": "version",
        },
        ExpressionAttributeValues={
            ":userId": user_id,
            ":expectedVersion": expected_version,
        },
        ReturnValues="ALL_OLD",
    )

    return response.get("Attributes")
