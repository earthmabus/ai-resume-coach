from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

from core.config import get_config
from core.auth import assert_item_owner, current_user_id
from core.idempotency import (
    DISPOSITION_REPLAY_COMPLETED,
    DISPOSITION_REPLAY_IN_PROGRESS,
    complete_request,
    mark_request_retryable,
    request_fingerprint,
    reserve_request,
)
from core.keys import (
    match_sk,
    tailoring_pk,
    tailoring_sk,
    user_pk,
)
from core.outbox import build_resume_tailoring_outbox_event
from core.request_context import build_request_context
from core.responses import build_response, parse_body
from core.storage import (
    get_entity_by_id,
    table,
    update_item_and_put_outbox,
)


logger = logging.getLogger(__name__)

TAILOR_RESUME_OPERATION = "TAILOR_RESUME"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_match_for_user(
    *,
    user_id: str,
    match_id: str,
) -> dict | None:
    """
    Read the job match through its authoritative base-table key.
    """
    return table.get_item(
        Key={
            "pk": user_pk(user_id),
            "sk": match_sk(match_id),
        },
        ConsistentRead=True,
    ).get("Item")


def get_tailoring_for_match(
    *,
    match_id: str,
    tailoring_id: str,
) -> dict | None:
    """
    Read the stable tailoring item through its base-table key.
    """
    return table.get_item(
        Key={
            "pk": tailoring_pk(match_id),
            "sk": tailoring_sk(tailoring_id),
        },
        ConsistentRead=True,
    ).get("Item")


def tailor_resume(event):
    body = parse_body(event)

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    context = build_request_context(
        event,
        require_idempotency=True,
    )
    user_id = context.user_id

    match_id = str(body.get("matchId") or "").strip()

    if not match_id:
        return build_response(400, {"error": "matchId is required"})

    match_item = get_match_for_user(
        user_id=user_id,
        match_id=match_id,
    )

    if not match_item:
        return build_response(404, {"error": "job match not found"})

    if match_item.get("recordType") != "jobMatch":
        return build_response(
            400,
            {"error": "record is not a job match"},
        )

    if match_item.get("status") != "completed":
        return build_response(
            400,
            {
                "error": (
                    "job match must be completed before tailoring"
                )
            },
        )

    tailoring_id = str(
        match_item.get("tailoringId") or ""
    ).strip()

    if not tailoring_id:
        return build_response(
            404,
            {
                "error": (
                    "job match does not have a tailoring record"
                )
            },
        )

    provider = (
        body.get("analysisProvider")
        or match_item.get("provider")
        or os.getenv("ANALYSIS_PROVIDER", "rule-based")
    )

    request_hash = request_fingerprint(
        user_id=user_id,
        operation=TAILOR_RESUME_OPERATION,
        body={
            "matchId": match_id,
            "tailoringId": tailoring_id,
            "analysisProvider": provider,
        },
    )

    reservation = reserve_request(
        user_id=user_id,
        operation=TAILOR_RESUME_OPERATION,
        idempotency_key=context.idempotency_key,
        request_hash=request_hash,
        resource_id=tailoring_id,
        request_id=context.request_id,
        correlation_id=context.correlation_id,
        region=context.region,
    )

    if reservation.disposition == DISPOSITION_REPLAY_COMPLETED:
        return build_response(
            reservation.status_code or 202,
            reservation.response_body or {},
        )

    if reservation.disposition == DISPOSITION_REPLAY_IN_PROGRESS:
        return build_response(
            reservation.status_code or 202,
            reservation.response_body
            or {
                "tailoringId": reservation.resource_id,
                "matchId": match_id,
                "status": "processing",
            },
        )

    effective_correlation_id = (
        reservation.correlation_id
        or context.correlation_id
    )

    try:
        tailoring_item = get_tailoring_for_match(
            match_id=match_id,
            tailoring_id=tailoring_id,
        )

        if not tailoring_item:
            response_body = {
                "error": "tailoring record not found",
                "tailoringId": tailoring_id,
                "matchId": match_id,
            }

            complete_request(
                user_id=user_id,
                operation=TAILOR_RESUME_OPERATION,
                idempotency_key=context.idempotency_key,
                request_hash=request_hash,
                resource_id=tailoring_id,
                request_id=context.request_id,
                region=context.region,
                status_code=404,
                response_body=response_body,
            )

            return build_response(404, response_body)

        if tailoring_item.get("userId") != user_id:
            return build_response(403, {"error": "forbidden"})

        if tailoring_item.get("matchId") != match_id:
            raise RuntimeError(
                "Tailoring record does not belong to the job match"
            )

        current_status = tailoring_item.get("status")

        if current_status == "waiting":
            queued_at = utc_now()
            outbox_event = build_resume_tailoring_outbox_event(
                tailoring_id=tailoring_id,
                match_id=match_id,
                user_id=user_id,
                analysis_provider=provider,
                created_region=context.region,
                created_deployment_id=context.deployment_id,
                request_id=context.request_id,
                correlation_id=effective_correlation_id,
                created_at=queued_at,
            )

            queued = update_item_and_put_outbox(
                key={
                    "pk": tailoring_pk(match_id),
                    "sk": tailoring_sk(tailoring_id),
                },
                update_expression=(
                    "SET #status = :pendingDispatch, "
                    "provider = :provider, "
                    "analysisVersion = :analysisVersion, "
                    "updatedAt = :updatedAt, "
                    "updatedByRequestId = :requestId, "
                    "correlationId = if_not_exists("
                    "correlationId, :correlationId), "
                    "lastUpdatedRegion = :region, "
                    "lastUpdatedByDeploymentId = :deploymentId, "
                    "#version = if_not_exists(#version, :zero) + :one"
                ),
                condition_expression=(
                    "#status = :waiting "
                    "AND userId = :userId "
                    "AND matchId = :matchId"
                ),
                expression_attribute_names={
                    "#status": "status",
                    "#version": "version",
                },
                expression_attribute_values={
                    ":waiting": "waiting",
                    ":pendingDispatch": "QUEUED_PENDING_DISPATCH",
                    ":provider": provider,
                    ":analysisVersion": (
                        "resume-tailoring-queued-v2"
                    ),
                    ":updatedAt": queued_at,
                    ":requestId": context.request_id,
                    ":correlationId": effective_correlation_id,
                    ":region": context.region,
                    ":deploymentId": context.deployment_id,
                    ":userId": user_id,
                    ":matchId": match_id,
                    ":zero": 0,
                    ":one": 1,
                },
                outbox_item=outbox_event.item,
            )

            if queued:
                tailoring_item = {
                    **tailoring_item,
                    "status": "QUEUED_PENDING_DISPATCH",
                    "provider": provider,
                    "analysisVersion": (
                        "resume-tailoring-queued-v2"
                    ),
                    "updatedAt": queued_at,
                    "version": int(
                        tailoring_item.get("version", 0)
                    ) + 1,
                }
                current_status = "QUEUED_PENDING_DISPATCH"
            else:
                tailoring_item = get_tailoring_for_match(
                    match_id=match_id,
                    tailoring_id=tailoring_id,
                ) or tailoring_item
                current_status = tailoring_item.get("status")

        if current_status not in {
            "QUEUED_PENDING_DISPATCH",
            "processing",
            "WORKER_PROCESSING",
            "completed",
            "FAILED_RETRYABLE",
        }:
            raise RuntimeError(
                "Tailoring record is in an unsupported state"
            )

        response_body = {
            "tailoringId": tailoring_id,
            "matchId": match_id,
            "status": current_status,
            "version": int(tailoring_item.get("version", 1)),
            "createdAt": tailoring_item.get("createdAt", ""),
        }

        complete_request(
            user_id=user_id,
            operation=TAILOR_RESUME_OPERATION,
            idempotency_key=context.idempotency_key,
            request_hash=request_hash,
            resource_id=tailoring_id,
            request_id=context.request_id,
            region=context.region,
            status_code=202,
            response_body=response_body,
        )

        return build_response(202, response_body)

    except Exception:
        logger.exception(
            "Resume-tailoring activation failed",
            extra={
                "tailoringId": tailoring_id,
                "matchId": match_id,
                "requestId": context.request_id,
                "region": context.region,
            },
        )

        try:
            mark_request_retryable(
                user_id=user_id,
                operation=TAILOR_RESUME_OPERATION,
                idempotency_key=context.idempotency_key,
                request_hash=request_hash,
                resource_id=tailoring_id,
                request_id=context.request_id,
                region=context.region,
            )
        except Exception:
            logger.exception(
                "Could not mark tailoring request retryable",
                extra={
                    "tailoringId": tailoring_id,
                    "requestId": context.request_id,
                },
            )

        raise


def get_resume_tailoring(event):
    user_id = current_user_id(event)

    tailoring_id = event.get("pathParameters", {}).get("id")

    if not tailoring_id:
        return build_response(
            400,
            {"error": "tailoring id is required"},
        )

    item = get_entity_by_id(
        tailoring_id,
        "resumeTailoring",
    )

    if not item:
        return build_response(
            404,
            {"error": "tailoring not found"},
        )

    try:
        assert_item_owner(item, user_id)
    except PermissionError:
        return build_response(403, {"error": "forbidden"})

    return build_response(200, item)


def get_resume_tailoring_by_match(event):
    user_id = current_user_id(event)
    match_id = event.get("pathParameters", {}).get("matchId")

    if not match_id:
        return build_response(
            400,
            {"error": "match id is required"},
        )

    response = table.query(
        KeyConditionExpression=(
            Key("pk").eq(tailoring_pk(match_id))
            & Key("sk").begins_with("TAILORING#")
        ),
        ConsistentRead=True,
    )

    items = [
        item
        for item in response.get("Items", [])
        if item.get("userId") == user_id
    ]

    if not items:
        return build_response(
            404,
            {"error": "tailoring not found for match"},
        )

    items = sorted(
        items,
        key=lambda item: item.get("createdAt", ""),
        reverse=True,
    )

    return build_response(200, items[0])


def get_interview_prep_by_match(event):
    user_id = current_user_id(event)
    match_id = event.get("pathParameters", {}).get("matchId")

    if not match_id:
        return build_response(
            400,
            {"error": "match id is required"},
        )

    response = table.query(
        KeyConditionExpression=(
            Key("pk").eq(tailoring_pk(match_id))
            & Key("sk").begins_with("INTERVIEW#")
        ),
        ConsistentRead=True,
    )

    items = [
        item
        for item in response.get("Items", [])
        if item.get("userId") == user_id
    ]

    if not items:
        return build_response(
            404,
            {
                "error": (
                    "interview preparation not found for match"
                )
            },
        )

    items = sorted(
        items,
        key=lambda item: item.get("createdAt", ""),
        reverse=True,
    )

    return build_response(200, items[0])
