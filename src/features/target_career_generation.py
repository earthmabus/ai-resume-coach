from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from core.keys import base_keys, user_pk
from core.request_context import build_request_context
from core.responses import build_response, parse_body
from core.storage import table

DETAIL_FIELDS = (
    "keyResponsibilities",
    "requiredSkills",
    "certifications",
    "physicalRequirements",
    "technicalRequirements",
    "leadershipRequirements",
)
INPUT_FIELDS = (
    "roleTitle",
    "industry",
    "seniorityLevel",
    "workEnvironment",
    "careerGoalSummary",
)

sqs = boto3.client("sqs")
queue_url = os.getenv("RESUME_ANALYSIS_QUEUE_URL")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def generation_sk(generation_id: str) -> str:
    return f"TARGET_CAREER_GENERATION#{generation_id}"


def _path_generation_id(event: dict) -> str:
    return str(event.get("pathParameters", {}).get("id") or "").strip()


def _normalize_inputs(body: dict) -> dict[str, str]:
    return {field: str(body.get(field) or "").strip() for field in INPUT_FIELDS}


def generate_target_career_details(event):
    context = build_request_context(event)
    body = parse_body(event)
    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    inputs = _normalize_inputs(body)
    if not inputs["roleTitle"]:
        return build_response(400, {"error": "roleTitle is required"})
    if not queue_url:
        return build_response(500, {"error": "Async processing queue is not configured"})

    generation_id = str(uuid.uuid4())
    now = utc_now()
    provider = str(body.get("analysisProvider") or os.getenv("ANALYSIS_PROVIDER", "openai")).strip().lower()
    key = {"pk": user_pk(context.user_id), "sk": generation_sk(generation_id)}
    item = {
        **base_keys(
            pk=key["pk"],
            sk=key["sk"],
            entity_id=generation_id,
            record_type="targetCareerGeneration",
        ),
        "recordType": "targetCareerGeneration",
        "generationId": generation_id,
        "userId": context.user_id,
        "status": "QUEUED",
        "provider": provider,
        "model": os.getenv("OPENAI_MODEL", ""),
        "version": 1,
        "createdAt": now,
        "updatedAt": now,
        "createdByRequestId": context.request_id,
        "correlationId": context.correlation_id,
        "ownerRegion": context.region,
        "createdRegion": context.region,
        "createdByDeploymentId": context.deployment_id,
        "lastUpdatedRegion": context.region,
        "lastUpdatedByDeploymentId": context.deployment_id,
        **inputs,
        **{field: "" for field in DETAIL_FIELDS},
    }

    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(pk) AND attribute_not_exists(sk)",
        )
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({
                "schemaVersion": 1,
                "jobType": "targetCareerGeneration",
                "jobId": generation_id,
                "generationId": generation_id,
                "userId": context.user_id,
                "requestId": context.request_id,
                "correlationId": context.correlation_id,
                "ownerRegion": context.region,
                "sourceRegion": context.region,
                "submittedAt": now,
            }),
        )
    except Exception:
        try:
            table.delete_item(Key=key)
        except Exception:
            pass
        raise

    return build_response(202, {
        "generationId": generation_id,
        "status": "QUEUED",
        "message": "Target career details are being generated.",
    })


def get_target_career_generation(event):
    context = build_request_context(event)
    generation_id = _path_generation_id(event)
    if not generation_id:
        return build_response(400, {"error": "generation id is required"})

    item = table.get_item(
        Key={"pk": user_pk(context.user_id), "sk": generation_sk(generation_id)},
        ConsistentRead=True,
    ).get("Item")
    if not item or item.get("userId") != context.user_id:
        return build_response(404, {"error": "target career generation not found"})

    payload = {
        "generationId": generation_id,
        "status": item.get("status", ""),
        "provider": item.get("provider", ""),
        "model": item.get("model", ""),
        "errorMessage": item.get("errorMessage", ""),
        "updatedAt": item.get("updatedAt", ""),
    }
    for field in DETAIL_FIELDS:
        payload[field] = item.get(field, "")
    return build_response(200, payload)
