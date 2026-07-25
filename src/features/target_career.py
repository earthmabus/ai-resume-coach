from __future__ import annotations

import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from core.errors import ResourceConflictError
from core.keys import base_keys, target_career_sk, user_pk
from core.request_context import build_request_context
from core.responses import build_response, parse_body
from core.storage import table


TARGET_CAREER_FIELDS = (
    "roleTitle",
    "industry",
    "seniorityLevel",
    "workEnvironment",
    "keyResponsibilities",
    "requiredSkills",
    "certifications",
    "physicalRequirements",
    "technicalRequirements",
    "leadershipRequirements",
    "careerGoalSummary",
)


def is_conditional_failure(error: ClientError) -> bool:
    return (
        error.response.get("Error", {}).get("Code")
        == "ConditionalCheckFailedException"
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path_target_career_id(event: dict) -> str:
    return str(
        event.get("pathParameters", {}).get("id") or ""
    ).strip()


def _normalized_fields(body: dict) -> dict[str, str]:
    return {
        field: str(body.get(field) or "").strip()
        for field in TARGET_CAREER_FIELDS
    }


def _validate_required(fields: dict[str, str]):
    if fields["roleTitle"] and fields["industry"]:
        return None

    return build_response(
        400,
        {"error": "roleTitle and industry are required"},
    )


def _expected_version(body: dict):
    try:
        value = int(body.get("version"))
    except (TypeError, ValueError):
        return None, build_response(
            400,
            {"error": "version is required and must be an integer"},
        )

    if value < 0:
        return None, build_response(
            400,
            {"error": "version must be zero or greater"},
        )

    return value, None


def list_target_careers_for_user(user_id: str) -> list[dict]:
    response = table.query(
        KeyConditionExpression=(
            Key("pk").eq(user_pk(user_id))
            & Key("sk").begins_with("TARGET_CAREER#")
        ),
        ConsistentRead=True,
    )

    return sorted(
        response.get("Items", []),
        key=lambda item: (
            item.get("createdAt", ""),
            item.get("targetCareerId", ""),
        ),
    )


def get_target_career_for_user(
    user_id: str,
    target_career_id: str | None = None,
):
    """Return one owned target career.

    Callers that have not yet adopted explicit career selection receive the
    oldest career. RA-003 will remove that transitional behavior by requiring
    a targetCareerId from the resume-analysis request.
    """
    if target_career_id:
        response = table.get_item(
            Key={
                "pk": user_pk(user_id),
                "sk": target_career_sk(target_career_id),
            },
            ConsistentRead=True,
        )
        item = response.get("Item")
        if item and item.get("userId") == user_id:
            return item
        return None

    careers = list_target_careers_for_user(user_id)
    return careers[0] if careers else None


def list_target_careers(event):
    context = build_request_context(event)
    careers = list_target_careers_for_user(context.user_id)
    return build_response(200, {"targetCareers": careers})


def get_target_career(event):
    context = build_request_context(event)
    target_career_id = _path_target_career_id(event)

    if not target_career_id:
        return build_response(
            400,
            {"error": "target career id is required"},
        )

    item = get_target_career_for_user(
        context.user_id,
        target_career_id,
    )
    if not item:
        return build_response(
            404,
            {"error": "target career not found"},
        )

    item.setdefault("version", 1)
    return build_response(200, item)


def create_target_career(event):
    context = build_request_context(event)
    body = parse_body(event)
    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    fields = _normalized_fields(body)
    validation_error = _validate_required(fields)
    if validation_error:
        return validation_error

    target_career_id = str(uuid.uuid4())
    created_at = utc_now()
    keys = base_keys(
        pk=user_pk(context.user_id),
        sk=target_career_sk(target_career_id),
        entity_id=target_career_id,
        record_type="targetCareer",
    )
    item = {
        **keys,
        "recordType": "targetCareer",
        "targetCareerId": target_career_id,
        "userId": context.user_id,
        "version": 1,
        "createdAt": created_at,
        "updatedAt": created_at,
        "updatedByRequestId": context.request_id,
        "lastUpdatedRegion": context.region,
        "lastUpdatedByDeploymentId": context.deployment_id,
        **fields,
    }

    try:
        table.put_item(
            Item=item,
            ConditionExpression=(
                "attribute_not_exists(pk) AND attribute_not_exists(sk)"
            ),
        )
    except ClientError as error:
        if is_conditional_failure(error):
            raise ResourceConflictError(
                "A target career with this identifier already exists"
            )
        raise

    return build_response(201, item)


def update_target_career(event):
    context = build_request_context(event)
    target_career_id = _path_target_career_id(event)
    if not target_career_id:
        return build_response(
            400,
            {"error": "target career id is required"},
        )

    body = parse_body(event)
    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    fields = _normalized_fields(body)
    validation_error = _validate_required(fields)
    if validation_error:
        return validation_error

    expected_version, version_error = _expected_version(body)
    if version_error:
        return version_error

    updated_at = utc_now()
    names = {"#version": "version"}
    values = {
        ":userId": context.user_id,
        ":updatedAt": updated_at,
        ":requestId": context.request_id,
        ":region": context.region,
        ":deploymentId": context.deployment_id,
        ":expectedVersion": expected_version,
        ":one": 1,
    }
    assignments = [
        "updatedAt = :updatedAt",
        "updatedByRequestId = :requestId",
        "lastUpdatedRegion = :region",
        "lastUpdatedByDeploymentId = :deploymentId",
        "#version = #version + :one",
    ]
    for field, value in fields.items():
        token = f":{field}"
        assignments.append(f"{field} = {token}")
        values[token] = value

    try:
        response = table.update_item(
            Key={
                "pk": user_pk(context.user_id),
                "sk": target_career_sk(target_career_id),
            },
            UpdateExpression="SET " + ", ".join(assignments),
            ConditionExpression=(
                "userId = :userId AND #version = :expectedVersion"
            ),
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
    except ClientError as error:
        if is_conditional_failure(error):
            raise ResourceConflictError(
                "The target career changed or was deleted before your update was saved"
            )
        raise

    return build_response(200, response["Attributes"])


def delete_target_career(event):
    context = build_request_context(event)
    target_career_id = _path_target_career_id(event)
    if not target_career_id:
        return build_response(
            400,
            {"error": "target career id is required"},
        )

    body = parse_body(event)
    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    expected_version, version_error = _expected_version(body)
    if version_error:
        return version_error

    try:
        table.delete_item(
            Key={
                "pk": user_pk(context.user_id),
                "sk": target_career_sk(target_career_id),
            },
            ConditionExpression=(
                "userId = :userId AND #version = :expectedVersion"
            ),
            ExpressionAttributeNames={"#version": "version"},
            ExpressionAttributeValues={
                ":userId": context.user_id,
                ":expectedVersion": expected_version,
            },
        )
    except ClientError as error:
        if is_conditional_failure(error):
            raise ResourceConflictError(
                "The target career changed or was deleted before it could be deleted"
            )
        raise

    return build_response(200, {"deleted": True, "targetCareerId": target_career_id})
