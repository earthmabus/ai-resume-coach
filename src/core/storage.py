import os

import boto3
from boto3.dynamodb.conditions import Key

from core.keys import entity_gsi_pk

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("RESUME_ANALYSIS_TABLE"))

s3 = boto3.client("s3")
document_bucket = os.getenv("DOCUMENT_BUCKET")

sqs = boto3.client("sqs")
resume_analysis_queue_url = os.getenv("RESUME_ANALYSIS_QUEUE_URL")

def get_entity_by_id(entity_id, expected_record_type=None):
    response = table.query(
        IndexName="gsi1",
        KeyConditionExpression=Key("gsi1pk").eq(entity_gsi_pk(entity_id)),
    )

    items = response.get("Items", [])

    if expected_record_type:
        items = [
            item for item in items
            if item.get("recordType") == expected_record_type
        ]

    return items[0] if items else None
