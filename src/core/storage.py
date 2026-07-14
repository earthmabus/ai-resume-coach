import boto3
from boto3.dynamodb.conditions import Key

from core.config import get_config
from core.keys import entity_gsi_pk


config = get_config()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(config.table_name)

s3 = boto3.client("s3")
document_bucket = config.document_bucket

sqs = boto3.client("sqs")
resume_analysis_queue_url = config.processing_queue_url


def get_entity_by_id(entity_id, expected_record_type=None):
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
