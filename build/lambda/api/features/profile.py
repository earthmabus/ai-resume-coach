from __future__ import annotations

from datetime import datetime, timezone

from botocore.exceptions import ClientError

from core.errors import ResourceConflictError
from core.keys import profile_sk, user_pk
from core.request_context import build_request_context
from core.responses import build_response, parse_body
from core.storage import table


def is_conditional_failure(error: ClientError) -> bool:
    return (
        error.response.get("Error", {}).get("Code")
        == "ConditionalCheckFailedException"
    )


def get_profile(event):
    context = build_request_context(event)
    user_id = context.user_id

    response = table.get_item(
        Key={
            "pk": user_pk(user_id),
            "sk": profile_sk(),
        },
        ConsistentRead=True,
    )

    item = response.get("Item")

    if not item:
        return build_response(
            200,
            {
                "pk": user_pk(user_id),
                "sk": profile_sk(),
                "recordType": "userProfile",
                "userId": user_id,
                "version": 0,
                "name": "",
                "currentTitle": "",
                "targetTitle": "",
                "yearsExperience": "",
                "certifications": "",
                "preferredProvider": "openai",
                "resumeStyle": "executive",
            },
        )

    item.setdefault("version", 0)

    return build_response(200, item)


def update_profile(event):
    context = build_request_context(event)
    user_id = context.user_id
    body = parse_body(event)

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

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

    updated_at = datetime.now(timezone.utc).isoformat()

    try:
        response = table.update_item(
            Key={
                "pk": user_pk(user_id),
                "sk": profile_sk(),
            },
            UpdateExpression=(
                "SET recordType = :recordType, "
                "userId = :userId, "
                "createdAt = if_not_exists(createdAt, :updatedAt), "
                "updatedAt = :updatedAt, "
                "updatedByRequestId = :requestId, "
                "lastUpdatedRegion = :region, "
                "#name = :name, "
                "currentTitle = :currentTitle, "
                "targetTitle = :targetTitle, "
                "yearsExperience = :yearsExperience, "
                "certifications = :certifications, "
                "preferredProvider = :preferredProvider, "
                "resumeStyle = :resumeStyle, "
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
                "#name": "name",
                "#version": "version",
            },
            ExpressionAttributeValues={
                ":recordType": "userProfile",
                ":userId": user_id,
                ":updatedAt": updated_at,
                ":requestId": context.request_id,
                ":region": context.region,
                ":name": str(body.get("name") or "").strip(),
                ":currentTitle": str(
                    body.get("currentTitle") or ""
                ).strip(),
                ":targetTitle": str(
                    body.get("targetTitle") or ""
                ).strip(),
                ":yearsExperience": str(
                    body.get("yearsExperience") or ""
                ).strip(),
                ":certifications": str(
                    body.get("certifications") or ""
                ).strip(),
                ":preferredProvider": str(
                    body.get("preferredProvider") or "openai"
                ).strip(),
                ":resumeStyle": str(
                    body.get("resumeStyle") or "executive"
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
                "The profile changed before your update was saved"
            )

        raise

    return build_response(200, response["Attributes"])
