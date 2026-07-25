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


def public_profile(item: dict, *, user_id: str) -> dict:
    return {
        "pk": item.get("pk", user_pk(user_id)),
        "sk": item.get("sk", profile_sk()),
        "recordType": item.get("recordType", "userProfile"),
        "userId": user_id,
        "version": int(item.get("version", 0)),
        "firstName": str(item.get("firstName") or ""),
        "lastName": str(item.get("lastName") or ""),
        "preferredProvider": str(item.get("preferredProvider") or "openai"),
        **({"createdAt": item["createdAt"]} if item.get("createdAt") else {}),
        **({"updatedAt": item["updatedAt"]} if item.get("updatedAt") else {}),
    }


def get_profile(event):
    context = build_request_context(event)
    user_id = context.user_id

    response = table.get_item(
        Key={"pk": user_pk(user_id), "sk": profile_sk()},
        ConsistentRead=True,
    )

    return build_response(
        200,
        public_profile(response.get("Item") or {}, user_id=user_id),
    )


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
            {"error": "version is required and must be an integer"},
        )

    if expected_version < 0:
        return build_response(400, {"error": "version must be zero or greater"})

    first_name = str(body.get("firstName") or "").strip()
    last_name = str(body.get("lastName") or "").strip()
    preferred_provider = str(body.get("preferredProvider") or "openai").strip()

    if len(first_name) > 100 or len(last_name) > 100:
        return build_response(
            400,
            {"error": "First name and last name must be 100 characters or fewer"},
        )

    if preferred_provider not in {"openai", "rule-based"}:
        return build_response(
            400,
            {"error": "preferredProvider is not supported"},
        )

    updated_at = datetime.now(timezone.utc).isoformat()

    try:
        response = table.update_item(
            Key={"pk": user_pk(user_id), "sk": profile_sk()},
            UpdateExpression=(
                "SET recordType = :recordType, "
                "userId = :userId, "
                "createdAt = if_not_exists(createdAt, :updatedAt), "
                "updatedAt = :updatedAt, "
                "updatedByRequestId = :requestId, "
                "lastUpdatedRegion = :region, "
                "lastUpdatedByDeploymentId = :deploymentId, "
                "firstName = :firstName, "
                "lastName = :lastName, "
                "preferredProvider = :preferredProvider, "
                "#version = if_not_exists(#version, :zero) + :one"
            ),
            ConditionExpression=(
                "(attribute_not_exists(pk) AND attribute_not_exists(sk) "
                "AND :expectedVersion = :zero) OR "
                "(userId = :userId AND ("
                "#version = :expectedVersion OR "
                "(attribute_not_exists(#version) AND :expectedVersion = :zero)))"
            ),
            ExpressionAttributeNames={"#version": "version"},
            ExpressionAttributeValues={
                ":recordType": "userProfile",
                ":userId": user_id,
                ":updatedAt": updated_at,
                ":requestId": context.request_id,
                ":region": context.region,
                ":deploymentId": context.deployment_id,
                ":firstName": first_name,
                ":lastName": last_name,
                ":preferredProvider": preferred_provider,
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

    return build_response(
        200,
        public_profile(response["Attributes"], user_id=user_id),
    )
