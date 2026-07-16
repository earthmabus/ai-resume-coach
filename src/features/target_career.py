from __future__ import annotations

from datetime import datetime, timezone

from botocore.exceptions import ClientError

from core.config import get_config
from core.errors import ResourceConflictError
from core.keys import base_keys, target_career_sk, user_pk
from core.request_context import build_request_context
from core.responses import build_response, parse_body
from core.storage import table


def is_conditional_failure(error: ClientError) -> bool:
    return (
        error.response.get("Error", {}).get("Code")
        == "ConditionalCheckFailedException"
    )


def get_target_career_for_user(user_id):
    response = table.get_item(
        Key={
            "pk": user_pk(user_id),
            "sk": target_career_sk(),
        },
        ConsistentRead=True,
    )

    return response.get("Item")


def get_target_career(event):
    context = build_request_context(event)
    user_id = context.user_id

    item = get_target_career_for_user(user_id)

    if not item:
        return build_response(
            200,
            {
                "recordType": "targetCareer",
                "targetCareerId": (
                    f"target-career-{user_id}"
                ),
                "userId": user_id,
                "version": 0,
                "roleTitle": "",
                "industry": "",
                "seniorityLevel": "",
                "workEnvironment": "",
                "keyResponsibilities": "",
                "requiredSkills": "",
                "certifications": "",
                "physicalRequirements": "",
                "technicalRequirements": "",
                "leadershipRequirements": "",
                "careerGoalSummary": "",
            },
        )

    item.setdefault("version", 0)

    return build_response(200, item)


def update_target_career(event):
    context = build_request_context(event)
    user_id = context.user_id
    body = parse_body(event)

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    role_title = str(body.get("roleTitle") or "").strip()
    industry = str(body.get("industry") or "").strip()

    if not role_title or not industry:
        return build_response(
            400,
            {
                "error": (
                    "roleTitle and industry are required"
                )
            },
        )

    try:
        expected_version = int(body.get("version"))
    except (TypeError, ValueError):
        return build_response(
            400,
            {
                "error": (
                    "version is required and must be an integer"
                )
            },
        )

    if expected_version < 0:
        return build_response(
            400,
            {"error": "version must be zero or greater"},
        )

    target_career_id = f"target-career-{user_id}"
    updated_at = datetime.now(timezone.utc).isoformat()

    keys = base_keys(
        pk=user_pk(user_id),
        sk=target_career_sk(),
        entity_id=target_career_id,
        record_type="targetCareer",
    )

    try:
        response = table.update_item(
            Key={
                "pk": keys["pk"],
                "sk": keys["sk"],
            },
            UpdateExpression=(
                "SET gsi1pk = :gsi1pk, "
                "gsi1sk = :gsi1sk, "
                "recordType = :recordType, "
                "targetCareerId = :targetCareerId, "
                "userId = :userId, "
                "createdAt = if_not_exists(createdAt, :updatedAt), "
                "updatedAt = :updatedAt, "
                "updatedByRequestId = :requestId, "
                "lastUpdatedRegion = :region, "
"lastUpdatedByDeploymentId = :deploymentId, "
                "roleTitle = :roleTitle, "
                "industry = :industry, "
                "seniorityLevel = :seniorityLevel, "
                "workEnvironment = :workEnvironment, "
                "keyResponsibilities = :keyResponsibilities, "
                "requiredSkills = :requiredSkills, "
                "certifications = :certifications, "
                "physicalRequirements = :physicalRequirements, "
                "technicalRequirements = :technicalRequirements, "
                "leadershipRequirements = :leadershipRequirements, "
                "careerGoalSummary = :careerGoalSummary, "
                "#version = if_not_exists(#version, :zero) + :one"
            ),
            ConditionExpression=(
                "("
                "attribute_not_exists(pk) "
                "AND attribute_not_exists(sk) "
                "AND :expectedVersion = :zero"
                ") "
                "OR "
                "("
                "userId = :userId "
                "AND ("
                "#version = :expectedVersion "
                "OR ("
                "attribute_not_exists(#version) "
                "AND :expectedVersion = :zero"
                ")"
                ")"
                ")"
            ),
            ExpressionAttributeNames={
                "#version": "version",
            },
            ExpressionAttributeValues={
                ":gsi1pk": keys["gsi1pk"],
                ":gsi1sk": keys["gsi1sk"],
                ":recordType": "targetCareer",
                ":targetCareerId": target_career_id,
                ":userId": user_id,
                ":updatedAt": updated_at,
                ":requestId": context.request_id,
                ":region": context.region,
                ":deploymentId": context.deployment_id,
                ":roleTitle": role_title,
                ":industry": industry,
                ":seniorityLevel": str(
                    body.get("seniorityLevel") or ""
                ).strip(),
                ":workEnvironment": str(
                    body.get("workEnvironment") or ""
                ).strip(),
                ":keyResponsibilities": str(
                    body.get("keyResponsibilities") or ""
                ).strip(),
                ":requiredSkills": str(
                    body.get("requiredSkills") or ""
                ).strip(),
                ":certifications": str(
                    body.get("certifications") or ""
                ).strip(),
                ":physicalRequirements": str(
                    body.get("physicalRequirements") or ""
                ).strip(),
                ":technicalRequirements": str(
                    body.get("technicalRequirements") or ""
                ).strip(),
                ":leadershipRequirements": str(
                    body.get("leadershipRequirements") or ""
                ).strip(),
                ":careerGoalSummary": str(
                    body.get("careerGoalSummary") or ""
                ).strip(),
                ":expectedVersion": expected_version,
                ":zero": 0,
                ":one": 1,
            },
            ReturnValues="ALL_NEW",
        )
    except ClientError as error:
        if is_conditional_failure(error):
            raise ResourceConflictError(
                (
                    "The target career changed before "
                    "your update was saved"
                )
            )

        raise

    return build_response(200, response["Attributes"])
