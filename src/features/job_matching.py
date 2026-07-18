from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from core.config import get_config
from core.auth import assert_item_owner, current_user_id
from core.errors import ResourceConflictError
from core.idempotency import (
    DISPOSITION_REPLAY_COMPLETED,
    DISPOSITION_REPLAY_IN_PROGRESS,
    complete_request,
    mark_request_retryable,
    request_fingerprint,
    reserve_request,
)
from core.keys import (
    base_keys,
    interview_sk,
    match_sk,
    resume_sk,
    tailoring_pk,
    tailoring_sk,
    user_pk,
)
from core.outbox import build_job_match_outbox_event
from core.request_context import build_request_context
from core.responses import build_response, parse_body
from core.storage import (
    get_entity_by_id,
    put_items_and_outbox_if_absent,
    put_item_if_absent,
    table,
)


logger = logging.getLogger(__name__)

MATCH_JOB_DESCRIPTION_OPERATION = "MATCH_JOB_DESCRIPTION"


def is_conditional_failure(error: ClientError) -> bool:
    return (
        error.response.get("Error", {}).get("Code")
        == "ConditionalCheckFailedException"
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_child_id(
    *,
    match_id: str,
    child_type: str,
) -> str:
    """
    Create a deterministic child identifier from the stable match ID.

    Retrying the same idempotent request therefore produces the same
    tailoring and interview-preparation IDs.
    """
    return str(
        uuid.uuid5(
            uuid.UUID(match_id),
            child_type,
        )
    )


def get_resume_for_user(
    *,
    user_id: str,
    analysis_id: str,
) -> dict | None:
    """
    Read the résumé directly through its authoritative base-table key.
    """
    return table.get_item(
        Key={
            "pk": user_pk(user_id),
            "sk": resume_sk(analysis_id),
        },
        ConsistentRead=True,
    ).get("Item")


def get_match_for_user(
    *,
    user_id: str,
    match_id: str,
) -> dict | None:
    """
    Read a job match directly through its authoritative base-table key.
    """
    return table.get_item(
        Key={
            "pk": user_pk(user_id),
            "sk": match_sk(match_id),
        },
        ConsistentRead=True,
    ).get("Item")


def ensure_child_item(
    *,
    item: dict,
    request_hash: str,
    child_description: str,
) -> dict:
    """
    Conditionally create a child item.

    When the item already exists, accept it only when it belongs to the
    same logical idempotent request.
    """
    if put_item_if_absent(item):
        return item

    existing = table.get_item(
        Key={
            "pk": item["pk"],
            "sk": item["sk"],
        },
        ConsistentRead=True,
    ).get("Item")

    if (
        not existing
        or existing.get("createdByRequestHash") != request_hash
    ):
        raise RuntimeError(
            f"{child_description} identifier already exists"
        )

    return existing


def match_job_description(event):
    body = parse_body(event)

    if body is None:
        return build_response(400, {"error": "Invalid JSON body"})

    context = build_request_context(
        event,
        require_idempotency=True,
    )
    user_id = context.user_id

    analysis_id = str(body.get("analysisId") or "").strip()
    job_name = (
        str(body.get("jobName") or "").strip()
        or "Untitled Job"
    )
    job_url = str(body.get("jobUrl") or "").strip()
    job_description_text = str(
        body.get("jobDescriptionText") or ""
    ).strip()
    requested_provider = (
        body.get("analysisProvider")
        or os.getenv("ANALYSIS_PROVIDER", "rule-based")
    )

    if not analysis_id:
        return build_response(
            400,
            {"error": "analysisId is required"},
        )

    if not job_description_text:
        return build_response(
            400,
            {"error": "jobDescriptionText is required"},
        )

    resume_item = get_resume_for_user(
        user_id=user_id,
        analysis_id=analysis_id,
    )

    if not resume_item:
        return build_response(
            404,
            {"error": "resume analysis not found"},
        )

    resume_text = str(
        resume_item.get("resumeText") or ""
    ).strip()

    if not resume_text:
        return build_response(
            400,
            {
                "error": (
                    "resume analysis does not contain resumeText"
                )
            },
        )

    fingerprint_body = {
        "analysisId": analysis_id,
        "jobName": job_name,
        "jobUrl": job_url,
        "jobDescriptionText": job_description_text,
        "analysisProvider": requested_provider,
    }

    request_hash = request_fingerprint(
        user_id=user_id,
        operation=MATCH_JOB_DESCRIPTION_OPERATION,
        body=fingerprint_body,
    )

    proposed_match_id = str(uuid.uuid4())

    reservation = reserve_request(
        user_id=user_id,
        operation=MATCH_JOB_DESCRIPTION_OPERATION,
        idempotency_key=context.idempotency_key,
        request_hash=request_hash,
        resource_id=proposed_match_id,
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
                "matchId": reservation.resource_id,
                "status": "processing",
            },
        )

    effective_correlation_id = (
        reservation.correlation_id
        or context.correlation_id
    )
    match_id = reservation.resource_id

    tailoring_id = stable_child_id(
        match_id=match_id,
        child_type="resume-tailoring",
    )
    interview_prep_id = stable_child_id(
        match_id=match_id,
        child_type="interview-preparation",
    )

    try:
        created_at = utc_now()

        match_key = {
            "pk": user_pk(user_id),
            "sk": match_sk(match_id),
        }

        existing_match = get_match_for_user(
            user_id=user_id,
            match_id=match_id,
        )

        if existing_match:
            if (
                existing_match.get("createdByRequestHash")
                != request_hash
            ):
                raise RuntimeError(
                    "Job match identifier already exists"
                )

            match_item = existing_match
            created_at = existing_match.get(
                "createdAt",
                created_at,
            )
        else:
            match_item = {
                **base_keys(
                    pk=match_key["pk"],
                    sk=match_key["sk"],
                    entity_id=match_id,
                    record_type="jobMatch",
                ),
                "recordType": "jobMatch",
                "userId": user_id,
                "analysisId": match_id,
                "matchId": match_id,
                "resumeAnalysisId": analysis_id,
                "tailoringId": tailoring_id,
                "interviewPrepId": interview_prep_id,
                "createdAt": created_at,
                "updatedAt": created_at,
                "createdByRequestId": context.request_id,
                "updatedByRequestId": context.request_id,
                "correlationId": effective_correlation_id,
                "createdByRequestHash": request_hash,
                "createdRegion": context.region,
                "createdByDeploymentId": context.deployment_id,
                "lastUpdatedRegion": context.region,
                "lastUpdatedByDeploymentId": context.deployment_id,
                "version": 1,
                "status": "QUEUED_PENDING_DISPATCH",
                "jobName": job_name,
                "jobUrl": job_url,
                "provider": requested_provider,
                "model": os.getenv("OPENAI_MODEL", ""),
                "analysisVersion": "job-match-queued-v2",
                "analysisDurationMs": 0,
                "matchScore": 0,
                "leadershipMatchScore": 0,
                "technicalMatchScore": 0,
                "architectureMatchScore": 0,
                "atsKeywordScore": 0,
                "matchedKeywords": [],
                "missingKeywords": [],
                "leadershipGaps": [],
                "technicalGaps": [],
                "recommendedResumeChanges": [
                    (
                        "Job match has been queued for "
                        "asynchronous AI analysis."
                    )
                ],
                "executiveSummary": "Job match is processing.",
                "jobDescriptionText": job_description_text,
                "resumeName": resume_item.get(
                    "resumeName",
                    "Untitled Resume",
                ),
                "resumeSourceType": resume_item.get(
                    "sourceType",
                    "",
                ),
                "resumeScore": resume_item.get("score", 0),
                "resumeCreatedAt": resume_item.get(
                    "createdAt",
                    "",
                ),
                "resumeFileName": resume_item.get(
                    "fileName",
                    "",
                ),
                "resumeDocumentBucket": resume_item.get(
                    "documentBucket",
                    "",
                ),
                "resumeDocumentKey": resume_item.get(
                    "documentKey",
                    "",
                ),
                "resumeText": resume_text,
            }

            # The match and both child records are created below in the
            # same transaction as the deterministic outbox event.
            pass

        tailoring_item = {
            **base_keys(
                pk=tailoring_pk(match_id),
                sk=tailoring_sk(tailoring_id),
                entity_id=tailoring_id,
                record_type="resumeTailoring",
            ),
            "recordType": "resumeTailoring",
            "userId": user_id,
            "analysisId": tailoring_id,
            "tailoringId": tailoring_id,
            "matchId": match_id,
            "resumeAnalysisId": analysis_id,
            "createdAt": created_at,
            "updatedAt": created_at,
            "createdByRequestId": context.request_id,
            "updatedByRequestId": context.request_id,
            "correlationId": effective_correlation_id,
            "createdByRequestHash": request_hash,
            "createdRegion": context.region,
                "createdByDeploymentId": context.deployment_id,
            "lastUpdatedRegion": context.region,
                "lastUpdatedByDeploymentId": context.deployment_id,
            "version": 1,
            "status": "waiting",
            "provider": requested_provider,
            "model": os.getenv("OPENAI_MODEL", ""),
            "analysisVersion": "resume-tailoring-waiting-v2",
            "analysisDurationMs": 0,
            "jobName": job_name,
            "jobUrl": job_url,
            "resumeName": resume_item.get(
                "resumeName",
                "Untitled Resume",
            ),
            "resumeText": resume_text,
            "jobDescriptionText": job_description_text,
            "resumeDocumentBucket": resume_item.get(
                "documentBucket",
                "",
            ),
            "resumeDocumentKey": resume_item.get(
                "documentKey",
                "",
            ),
            "resumeFileName": resume_item.get(
                "fileName",
                "",
            ),
            "tailoredExecutiveSummary": "",
            "tailoredResumeBullets": [],
            "keywordsToAdd": [],
            "rolePositioningAdvice": [],
            "atsOptimizationAdvice": [],
            "rewriteWarnings": [],
        }


        interview_prep_item = {
            **base_keys(
                pk=tailoring_pk(match_id),
                sk=interview_sk(interview_prep_id),
                entity_id=interview_prep_id,
                record_type="interviewPreparation",
            ),
            "recordType": "interviewPreparation",
            "userId": user_id,
            "analysisId": interview_prep_id,
            "interviewPrepId": interview_prep_id,
            "matchId": match_id,
            "resumeAnalysisId": analysis_id,
            "createdAt": created_at,
            "updatedAt": created_at,
            "createdByRequestId": context.request_id,
            "updatedByRequestId": context.request_id,
            "correlationId": effective_correlation_id,
            "createdByRequestHash": request_hash,
            "createdRegion": context.region,
                "createdByDeploymentId": context.deployment_id,
            "lastUpdatedRegion": context.region,
                "lastUpdatedByDeploymentId": context.deployment_id,
            "version": 1,
            "status": "waiting",
            "provider": requested_provider,
            "model": os.getenv("OPENAI_MODEL", ""),
            "analysisVersion": "interview-prep-waiting-v2",
            "analysisDurationMs": 0,
            "jobName": job_name,
            "jobUrl": job_url,
            "resumeName": resume_item.get(
                "resumeName",
                "Untitled Resume",
            ),
            "resumeText": resume_text,
            "jobDescriptionText": job_description_text,
            "behavioralQuestions": [],
            "leadershipQuestions": [],
            "systemDesignQuestions": [],
            "cloudArchitectureQuestions": [],
            "securityQuestions": [],
            "resumeSpecificQuestions": [],
            "jobSpecificQuestions": [],
            "interviewReadinessSummary": "",
        }

        if existing_match:
            ensure_child_item(
                item=tailoring_item,
                request_hash=request_hash,
                child_description="Resume tailoring",
            )
            ensure_child_item(
                item=interview_prep_item,
                request_hash=request_hash,
                child_description="Interview preparation",
            )
        else:
            outbox_event = build_job_match_outbox_event(
                match_id=match_id,
                resume_analysis_id=analysis_id,
                user_id=user_id,
                analysis_provider=requested_provider,
                created_region=context.region,
                created_deployment_id=context.deployment_id,
                request_id=context.request_id,
                correlation_id=effective_correlation_id,
                created_at=created_at,
            )

            created = put_items_and_outbox_if_absent(
                items=[
                    match_item,
                    tailoring_item,
                    interview_prep_item,
                ],
                outbox_item=outbox_event.item,
            )

            if not created:
                existing_match = get_match_for_user(
                    user_id=user_id,
                    match_id=match_id,
                )

                if (
                    not existing_match
                    or existing_match.get(
                        "createdByRequestHash"
                    )
                    != request_hash
                ):
                    raise RuntimeError(
                        "Job match identifier already exists"
                    )

                match_item = existing_match
                created_at = existing_match.get(
                    "createdAt",
                    created_at,
                )

                ensure_child_item(
                    item=tailoring_item,
                    request_hash=request_hash,
                    child_description="Resume tailoring",
                )
                ensure_child_item(
                    item=interview_prep_item,
                    request_hash=request_hash,
                    child_description="Interview preparation",
                )

        current_status = match_item.get("status")

        if current_status not in {
            "QUEUED_PENDING_DISPATCH",
            "processing",
            "WORKER_PROCESSING",
            "RESULT_READY_PENDING_CHILD_DISPATCH",
            "completed",
            "FAILED_RETRYABLE",
        }:
            raise RuntimeError(
                "Job match is in an unsupported dispatch state"
            )

        response_body = {
            "matchId": match_id,
            "analysisId": match_id,
            "resumeAnalysisId": analysis_id,
            "tailoringId": tailoring_id,
            "interviewPrepId": interview_prep_id,
            "status": current_status,
            "version": int(match_item.get("version", 1)),
            "jobName": match_item.get(
                "jobName",
                job_name,
            ),
            "jobUrl": match_item.get(
                "jobUrl",
                job_url,
            ),
            "createdAt": match_item.get(
                "createdAt",
                created_at,
            ),
        }

        complete_request(
            user_id=user_id,
            operation=MATCH_JOB_DESCRIPTION_OPERATION,
            idempotency_key=context.idempotency_key,
            request_hash=request_hash,
            resource_id=match_id,
            request_id=context.request_id,
            region=context.region,
            status_code=202,
            response_body=response_body,
        )

        return build_response(202, response_body)

    except Exception:
        logger.exception(
            "Job-match submission failed",
            extra={
                "matchId": match_id,
                "requestId": context.request_id,
                "region": context.region,
            },
        )

        try:
            mark_request_retryable(
                user_id=user_id,
                operation=MATCH_JOB_DESCRIPTION_OPERATION,
                idempotency_key=context.idempotency_key,
                request_hash=request_hash,
                resource_id=match_id,
                request_id=context.request_id,
                region=context.region,
            )
        except Exception:
            logger.exception(
                "Could not mark job-match request retryable",
                extra={
                    "matchId": match_id,
                    "requestId": context.request_id,
                    "region": context.region,
                },
            )

        raise


def list_job_matches(event):
    user_id = current_user_id(event)

    response = table.query(
        KeyConditionExpression=(
            Key("pk").eq(user_pk(user_id))
            & Key("sk").begins_with("MATCH#")
        )
    )

    matches = sorted(
        response.get("Items", []),
        key=lambda item: item.get("createdAt", ""),
        reverse=True,
    )

    return build_response(200, {"jobMatches": matches})


def get_job_match(event):
    user_id = current_user_id(event)
    match_id = event.get("pathParameters", {}).get("id")

    if not match_id:
        return build_response(
            400,
            {"error": "match id is required"},
        )

    item = get_entity_by_id(match_id, "jobMatch")

    if not item:
        return build_response(
            404,
            {"error": "job match not found"},
        )

    try:
        assert_item_owner(item, user_id)
    except PermissionError:
        return build_response(403, {"error": "forbidden"})

    return build_response(200, item)


def delete_job_match(event):
    context = build_request_context(event)
    user_id = context.user_id

    match_id = event.get(
        "pathParameters",
        {},
    ).get("id")

    if not match_id:
        return build_response(
            400,
            {"error": "match id is required"},
        )

    query_parameters = (
        event.get("queryStringParameters") or {}
    )

    try:
        expected_version = int(
            query_parameters.get("version")
        )
    except (TypeError, ValueError):
        return build_response(
            400,
            {
                "error": (
                    "version query parameter is required "
                    "and must be an integer"
                )
            },
        )

    if expected_version < 0:
        return build_response(
            400,
            {"error": "version must be zero or greater"},
        )

    match_key = {
        "pk": user_pk(user_id),
        "sk": match_sk(match_id),
    }

    existing = table.get_item(
        Key=match_key,
        ConsistentRead=True,
    ).get("Item")

    if not existing:
        return build_response(
            404,
            {"error": "job match not found"},
        )

    try:
        table.delete_item(
            Key=match_key,
            ConditionExpression=(
                "userId = :userId "
                "AND recordType = :recordType "
                "AND ("
                "#version = :expectedVersion "
                "OR ("
                "attribute_not_exists(#version) "
                "AND :expectedVersion = :zero"
                ")"
                ")"
            ),
            ExpressionAttributeNames={
                "#version": "version",
            },
            ExpressionAttributeValues={
                ":userId": user_id,
                ":recordType": "jobMatch",
                ":expectedVersion": expected_version,
                ":zero": 0,
            },
        )
    except ClientError as error:
        if is_conditional_failure(error):
            raise ResourceConflictError(
                (
                    "The job match changed before "
                    "it could be deleted"
                )
            )

        raise

    child_response = table.query(
        KeyConditionExpression=Key("pk").eq(
            tailoring_pk(match_id)
        ),
        ConsistentRead=True,
    )

    deleted_children = 0
    failed_children = 0

    for child in child_response.get("Items", []):
        try:
            table.delete_item(
                Key={
                    "pk": child["pk"],
                    "sk": child["sk"],
                },
                ConditionExpression="userId = :userId",
                ExpressionAttributeValues={
                    ":userId": user_id,
                },
            )
            deleted_children += 1
        except ClientError as error:
            if is_conditional_failure(error):
                failed_children += 1
                continue

            raise

    return build_response(
        200,
        {
            "deleted": True,
            "matchId": match_id,
            "deletedVersion": expected_version,
            "deletedCount": deleted_children + 1,
            "deletedChildren": deleted_children,
            "failedChildren": failed_children,
        },
    )


def delete_all_job_matches(event):
    context = build_request_context(event)
    user_id = context.user_id

    response = table.query(
        KeyConditionExpression=(
            Key("pk").eq(user_pk(user_id))
            & Key("sk").begins_with("MATCH#")
        ),
        ConsistentRead=True,
    )

    matches = response.get("Items", [])

    requested = len(matches)
    deleted = 0
    conflicted = 0
    failed = 0
    deleted_children = 0
    failed_children = 0

    for match in matches:
        match_id = str(match.get("matchId") or "").strip()
        expected_version = int(match.get("version", 0))

        if not match_id:
            failed += 1
            continue

        #
        # Delete derived child records before deleting the parent.
        #
        # If the parent changes concurrently, the conditional parent
        # deletion will fail and the visible match remains available.
        # The waiting/generated child records can be recreated from the
        # parent workflow if necessary.
        #
        try:
            child_response = table.query(
                KeyConditionExpression=Key("pk").eq(
                    tailoring_pk(match_id)
                ),
                ConsistentRead=True,
            )
        except ClientError:
            logger.exception(
                "Could not query job-match children during bulk deletion",
                extra={
                    "matchId": match_id,
                    "requestId": context.request_id,
                    "region": context.region,
                },
            )

            failed += 1
            continue

        child_cleanup_failed = False

        for child in child_response.get("Items", []):
            try:
                table.delete_item(
                    Key={
                        "pk": child["pk"],
                        "sk": child["sk"],
                    },
                    ConditionExpression=(
                        "userId = :userId "
                        "AND matchId = :matchId"
                    ),
                    ExpressionAttributeValues={
                        ":userId": user_id,
                        ":matchId": match_id,
                    },
                )

                deleted_children += 1

            except ClientError as error:
                if is_conditional_failure(error):
                    failed_children += 1
                    child_cleanup_failed = True
                    continue

                logger.exception(
                    "Job-match child deletion failed",
                    extra={
                        "matchId": match_id,
                        "childRecordType": child.get(
                            "recordType"
                        ),
                        "requestId": context.request_id,
                        "region": context.region,
                    },
                )

                failed_children += 1
                child_cleanup_failed = True

        if child_cleanup_failed:
            failed += 1
            continue

        try:
            table.delete_item(
                Key={
                    "pk": match["pk"],
                    "sk": match["sk"],
                },
                ConditionExpression=(
                    "userId = :userId "
                    "AND recordType = :recordType "
                    "AND ("
                    "#version = :expectedVersion "
                    "OR ("
                    "attribute_not_exists(#version) "
                    "AND :expectedVersion = :zero"
                    ")"
                    ")"
                ),
                ExpressionAttributeNames={
                    "#version": "version",
                },
                ExpressionAttributeValues={
                    ":userId": user_id,
                    ":recordType": "jobMatch",
                    ":expectedVersion": expected_version,
                    ":zero": 0,
                },
            )

            deleted += 1

        except ClientError as error:
            if is_conditional_failure(error):
                conflicted += 1
                continue

            logger.exception(
                "Bulk job-match deletion failed",
                extra={
                    "matchId": match_id,
                    "requestId": context.request_id,
                    "region": context.region,
                },
            )

            failed += 1

    return build_response(
        200,
        {
            "requested": requested,
            "deleted": deleted,
            "conflicted": conflicted,
            "failed": failed,
            "deletedChildren": deleted_children,
            "failedChildren": failed_children,
            "recordType": "jobMatchBundle",
        },
    )
