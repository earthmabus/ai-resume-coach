from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from providers.factory import get_analysis_provider


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("RESUME_ANALYSIS_TABLE"))

sqs = boto3.client("sqs")
queue_url = os.getenv("RESUME_ANALYSIS_QUEUE_URL")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


STATUS_COMPLETED = "completed"
STATUS_FAILED_RETRYABLE = "FAILED_RETRYABLE"
STATUS_WORKER_PROCESSING = "WORKER_PROCESSING"
STATUS_RESULT_READY = "RESULT_READY_PENDING_CHILD_DISPATCH"

DEFAULT_LEASE_SECONDS = int(
    os.getenv("WORKER_PROCESSING_LEASE_SECONDS", "300")
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def epoch_seconds() -> int:
    return int(time.time())


def to_dynamodb_value(value):
    if isinstance(value, float):
        return Decimal(str(value))

    if isinstance(value, dict):
        return {
            key: to_dynamodb_value(child)
            for key, child in value.items()
        }

    if isinstance(value, list):
        return [
            to_dynamodb_value(child)
            for child in value
        ]

    return value


def entity_gsi_pk(entity_id):
    return f"ENTITY#{entity_id}"


def user_pk(user_id):
    return f"USER#{user_id}"


def resume_sk(analysis_id):
    return f"RESUME#{analysis_id}"


def match_sk(match_id):
    return f"MATCH#{match_id}"


def tailoring_pk(match_id):
    return f"MATCH#{match_id}"


def tailoring_sk(tailoring_id):
    return f"TAILORING#{tailoring_id}"


def interview_sk(interview_prep_id):
    return f"INTERVIEW#{interview_prep_id}"


def is_conditional_failure(error: ClientError) -> bool:
    return (
        error.response.get("Error", {}).get("Code")
        == "ConditionalCheckFailedException"
    )


def get_entity_by_id(
    entity_id,
    expected_record_type=None,
):
    """
    Compatibility fallback for older messages that do not contain enough
    data to derive the base-table key.

    New messages should include userId and/or matchId so the worker can
    perform a strongly consistent base-table read instead.
    """
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
            if item.get("recordType")
            == expected_record_type
        ]

    return items[0] if items else None


def derive_job_identity(body: dict) -> dict:
    job_type = body.get("jobType", "resumeAnalysis")
    user_id = str(body.get("userId") or "").strip()
    match_id = str(body.get("matchId") or "").strip()

    if job_type == "resumeAnalysis":
        record_id = str(
            body.get("analysisId") or ""
        ).strip()

        if user_id and record_id:
            return {
                "jobType": job_type,
                "recordType": "resumeAnalysis",
                "recordId": record_id,
                "key": {
                    "pk": user_pk(user_id),
                    "sk": resume_sk(record_id),
                },
            }

    elif job_type == "jobMatch":
        record_id = str(
            body.get("matchId") or ""
        ).strip()

        if user_id and record_id:
            return {
                "jobType": job_type,
                "recordType": "jobMatch",
                "recordId": record_id,
                "key": {
                    "pk": user_pk(user_id),
                    "sk": match_sk(record_id),
                },
            }

    elif job_type == "resumeTailoring":
        record_id = str(
            body.get("tailoringId") or ""
        ).strip()

        if match_id and record_id:
            return {
                "jobType": job_type,
                "recordType": "resumeTailoring",
                "recordId": record_id,
                "key": {
                    "pk": tailoring_pk(match_id),
                    "sk": tailoring_sk(record_id),
                },
            }

    elif job_type == "interviewPreparation":
        record_id = str(
            body.get("interviewPrepId") or ""
        ).strip()

        if match_id and record_id:
            return {
                "jobType": job_type,
                "recordType": "interviewPreparation",
                "recordId": record_id,
                "key": {
                    "pk": tailoring_pk(match_id),
                    "sk": interview_sk(record_id),
                },
            }

    else:
        raise ValueError(
            f"Unsupported jobType: {job_type}"
        )

    record_id = (
        body.get("analysisId")
        or body.get("matchId")
        or body.get("tailoringId")
        or body.get("interviewPrepId")
    )

    if not record_id:
        raise ValueError(
            f"Record identifier is missing for {job_type}"
        )

    expected_record_type = {
        "resumeAnalysis": "resumeAnalysis",
        "jobMatch": "jobMatch",
        "resumeTailoring": "resumeTailoring",
        "interviewPreparation": (
            "interviewPreparation"
        ),
    }[job_type]

    item = get_entity_by_id(
        record_id,
        expected_record_type,
    )

    if not item:
        raise ValueError(
            f"{expected_record_type} not found: {record_id}"
        )

    return {
        "jobType": job_type,
        "recordType": expected_record_type,
        "recordId": record_id,
        "key": {
            "pk": item["pk"],
            "sk": item["sk"],
        },
    }


def get_item_strong(key: dict) -> dict | None:
    return table.get_item(
        Key=key,
        ConsistentRead=True,
    ).get("Item")


def claimable_statuses(job_type: str) -> set[str]:
    common = {
        "processing",
        "QUEUED_PENDING_DISPATCH",
        STATUS_FAILED_RETRYABLE,
    }

    if job_type in {
        "resumeTailoring",
        "interviewPreparation",
    }:
        common.add("waiting")

    if job_type == "jobMatch":
        common.add(STATUS_RESULT_READY)

    return common


def claim_job(identity: dict) -> dict:
    """
    Conditionally claim a job before invoking an AI provider.

    Returns:
      {
        "disposition": "CLAIMED" | "SKIP",
        "item": ...,
        "attemptId": ...,
        "priorStatus": ...
      }
    """
    key = identity["key"]
    job_type = identity["jobType"]

    item = get_item_strong(key)

    if not item:
        raise ValueError(
            f"{identity['recordType']} not found: "
            f"{identity['recordId']}"
        )

    current_status = item.get("status")
    current_version = int(item.get("version", 0))

    if current_status == STATUS_COMPLETED:
        return {
            "disposition": "SKIP",
            "item": item,
            "attemptId": None,
            "priorStatus": current_status,
        }

    if current_status == STATUS_WORKER_PROCESSING:
        lease_expires_at = int(
            item.get("processingLeaseExpiresAt", 0)
        )

        if lease_expires_at > epoch_seconds():
            return {
                "disposition": "SKIP",
                "item": item,
                "attemptId": None,
                "priorStatus": current_status,
            }

    elif current_status not in claimable_statuses(
        job_type
    ):
        raise RuntimeError(
            f"{identity['recordType']} is not claimable "
            f"from status {current_status!r}"
        )

    attempt_id = str(uuid.uuid4())
    claimed_at = utc_now()
    lease_expires_at = (
        epoch_seconds() + DEFAULT_LEASE_SECONDS
    )

    try:
        response = table.update_item(
            Key=key,
            UpdateExpression=(
                "SET #status = :workerProcessing, "
                "processingAttemptId = :attemptId, "
                "processingStartedAt = :claimedAt, "
                "processingLeaseExpiresAt = :leaseExpiresAt, "
                "updatedAt = :claimedAt, "
                "lastUpdatedRegion = :region, "
                "#version = if_not_exists(#version, :zero) + :one"
            ),
            ConditionExpression=(
                "#status = :expectedStatus "
                "AND ("
                "#version = :expectedVersion "
                "OR ("
                "attribute_not_exists(#version) "
                "AND :expectedVersion = :zero"
                ")"
                ")"
            ),
            ExpressionAttributeNames={
                "#status": "status",
                "#version": "version",
            },
            ExpressionAttributeValues={
                ":workerProcessing": (
                    STATUS_WORKER_PROCESSING
                ),
                ":attemptId": attempt_id,
                ":claimedAt": claimed_at,
                ":leaseExpiresAt": lease_expires_at,
                ":region": os.getenv(
                    "AWS_REGION",
                    "unknown",
                ),
                ":expectedStatus": current_status,
                ":expectedVersion": current_version,
                ":zero": 0,
                ":one": 1,
            },
            ReturnValues="ALL_NEW",
        )
    except ClientError as error:
        if not is_conditional_failure(error):
            raise

        raced_item = get_item_strong(key)

        if raced_item and raced_item.get(
            "status"
        ) in {
            STATUS_COMPLETED,
            STATUS_WORKER_PROCESSING,
        }:
            return {
                "disposition": "SKIP",
                "item": raced_item,
                "attemptId": None,
                "priorStatus": raced_item.get(
                    "status"
                ),
            }

        raise

    return {
        "disposition": "CLAIMED",
        "item": response["Attributes"],
        "attemptId": attempt_id,
        "priorStatus": current_status,
    }


def update_claimed_record(
    *,
    key: dict,
    attempt_id: str,
    status: str,
    fields: dict[str, Any],
    remove_processing_metadata: bool = True,
) -> dict:
    names = {
        "#status": "status",
        "#version": "version",
    }

    values = {
        ":status": status,
        ":attemptId": attempt_id,
        ":updatedAt": utc_now(),
        ":region": os.getenv(
            "AWS_REGION",
            "unknown",
        ),
        ":zero": 0,
        ":one": 1,
    }

    assignments = [
        "#status = :status",
        "updatedAt = :updatedAt",
        "lastUpdatedRegion = :region",
        "#version = if_not_exists(#version, :zero) + :one",
    ]

    for index, (field_name, value) in enumerate(
        fields.items()
    ):
        name_key = f"#field{index}"
        value_key = f":field{index}"

        names[name_key] = field_name
        values[value_key] = to_dynamodb_value(value)

        assignments.append(
            f"{name_key} = {value_key}"
        )

    update_expression = (
        "SET " + ", ".join(assignments)
    )

    if remove_processing_metadata:
        update_expression += (
            " REMOVE processingAttemptId, "
            "processingStartedAt, "
            "processingLeaseExpiresAt"
        )

    response = table.update_item(
        Key=key,
        UpdateExpression=update_expression,
        ConditionExpression=(
            "#status = :workerProcessing "
            "AND processingAttemptId = :attemptId"
        ),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues={
            **values,
            ":workerProcessing": (
                STATUS_WORKER_PROCESSING
            ),
        },
        ReturnValues="ALL_NEW",
    )

    return response["Attributes"]


def mark_claim_failed(
    *,
    key: dict,
    attempt_id: str,
    error_message: str,
):
    try:
        update_claimed_record(
            key=key,
            attempt_id=attempt_id,
            status=STATUS_FAILED_RETRYABLE,
            fields={
                "errorMessage": error_message[:2000],
                "failedAt": utc_now(),
            },
        )
    except ClientError as error:
        if is_conditional_failure(error):
            logger.warning(
                "Could not mark worker attempt failed "
                "because ownership changed: %s",
                attempt_id,
            )
            return

        raise


def process_resume_analysis(
    *,
    identity: dict,
    item: dict,
    attempt_id: str,
):
    analysis_id = identity["recordId"]

    resume_text = str(
        item.get("resumeText") or ""
    ).strip()

    if not resume_text:
        raise ValueError(
            f"No resumeText found for analysis: "
            f"{analysis_id}"
        )

    target_career = item.get("targetCareer")

    if not target_career:
        raise ValueError(
            f"Target career not found for analysis: "
            f"{analysis_id}"
        )

    requested_provider = (
        item.get("requestedProvider")
        or item.get("provider")
    )

    started = time.perf_counter()

    provider = get_analysis_provider(
        requested_provider
    )
    analysis_result = provider.analyze(
        resume_text,
        target_career,
    )

    duration_ms = int(
        (time.perf_counter() - started) * 1000
    )

    update_claimed_record(
        key=identity["key"],
        attempt_id=attempt_id,
        status=STATUS_COMPLETED,
        fields={
            "provider": analysis_result["provider"],
            "model": analysis_result.get("model", ""),
            "analysisVersion": analysis_result[
                "analysisVersion"
            ],
            "score": analysis_result["score"],
            "wordCount": analysis_result["wordCount"],
            "analysisDurationMs": duration_ms,
            "dynamicScores": analysis_result.get(
                "dynamicScores",
                [],
            ),
            "roleFitSummary": analysis_result.get(
                "roleFitSummary",
                "",
            ),
            "roleSpecificGaps": analysis_result.get(
                "roleSpecificGaps",
                [],
            ),
            "strengths": analysis_result["strengths"],
            "recommendations": analysis_result[
                "recommendations"
            ],
            "executiveSummary": analysis_result.get(
                "executiveSummary",
                "",
            ),
            "targetRoleTitle": target_career.get(
                "roleTitle",
                "",
            ),
            "targetIndustry": target_career.get(
                "industry",
                "",
            ),
            "completedAt": utc_now(),
        },
    )


def dispatch_child_job(
    *,
    child_item: dict,
    message_body: dict,
):
    key = {
        "pk": child_item["pk"],
        "sk": child_item["sk"],
    }

    current = get_item_strong(key)

    if not current:
        raise ValueError(
            "Child record disappeared before dispatch"
        )

    status = current.get("status")

    if status in {
        "processing",
        STATUS_WORKER_PROCESSING,
        STATUS_COMPLETED,
    }:
        return

    if status not in {
        "waiting",
        "QUEUED_PENDING_DISPATCH",
        STATUS_FAILED_RETRYABLE,
    }:
        raise RuntimeError(
            "Child record is in an unsupported "
            f"dispatch status: {status!r}"
        )

    if status != "QUEUED_PENDING_DISPATCH":
        try:
            table.update_item(
                Key=key,
                UpdateExpression=(
                    "SET #status = :pending, "
                    "updatedAt = :updatedAt, "
                    "#version = if_not_exists("
                    "#version, :zero) + :one"
                ),
                ConditionExpression=(
                    "#status = :expectedStatus"
                ),
                ExpressionAttributeNames={
                    "#status": "status",
                    "#version": "version",
                },
                ExpressionAttributeValues={
                    ":pending": (
                        "QUEUED_PENDING_DISPATCH"
                    ),
                    ":expectedStatus": status,
                    ":updatedAt": utc_now(),
                    ":zero": 0,
                    ":one": 1,
                },
            )
        except ClientError as error:
            if not is_conditional_failure(error):
                raise

            current = get_item_strong(key)

            if current and current.get(
                "status"
            ) in {
                "processing",
                STATUS_WORKER_PROCESSING,
                STATUS_COMPLETED,
            }:
                return

            if (
                not current
                or current.get("status")
                != "QUEUED_PENDING_DISPATCH"
            ):
                raise

    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message_body),
    )

    try:
        table.update_item(
            Key=key,
            UpdateExpression=(
                "SET #status = :processing, "
                "updatedAt = :updatedAt, "
                "#version = if_not_exists("
                "#version, :zero) + :one"
            ),
            ConditionExpression=(
                "#status = :pending"
            ),
            ExpressionAttributeNames={
                "#status": "status",
                "#version": "version",
            },
            ExpressionAttributeValues={
                ":processing": "processing",
                ":pending": "QUEUED_PENDING_DISPATCH",
                ":updatedAt": utc_now(),
                ":zero": 0,
                ":one": 1,
            },
        )
    except ClientError as error:
        if not is_conditional_failure(error):
            raise

        current = get_item_strong(key)

        if not current or current.get(
            "status"
        ) not in {
            "processing",
            STATUS_WORKER_PROCESSING,
            STATUS_COMPLETED,
        }:
            raise


def dispatch_job_match_children(
    *,
    match_item: dict,
):
    match_id = match_item["matchId"]
    user_id = match_item["userId"]

    tailoring_id = str(
        match_item.get("tailoringId") or ""
    ).strip()

    if tailoring_id:
        tailoring_key = {
            "pk": tailoring_pk(match_id),
            "sk": tailoring_sk(tailoring_id),
        }

        tailoring_item = get_item_strong(
            tailoring_key
        )

        if not tailoring_item:
            raise ValueError(
                f"Resume tailoring not found: "
                f"{tailoring_id}"
            )

        dispatch_child_job(
            child_item=tailoring_item,
            message_body={
                "schemaVersion": 1,
                "jobType": "resumeTailoring",
                "jobId": tailoring_id,
                "tailoringId": tailoring_id,
                "matchId": match_id,
                "userId": user_id,
                "analysisProvider": (
                    tailoring_item.get("provider")
                ),
                "sourceRegion": os.getenv(
                    "AWS_REGION",
                    "unknown",
                ),
                "submittedAt": utc_now(),
            },
        )

    interview_prep_id = str(
        match_item.get("interviewPrepId") or ""
    ).strip()

    if interview_prep_id:
        interview_key = {
            "pk": tailoring_pk(match_id),
            "sk": interview_sk(interview_prep_id),
        }

        interview_item = get_item_strong(
            interview_key
        )

        if not interview_item:
            raise ValueError(
                "Interview preparation not found: "
                f"{interview_prep_id}"
            )

        dispatch_child_job(
            child_item=interview_item,
            message_body={
                "schemaVersion": 1,
                "jobType": "interviewPreparation",
                "jobId": interview_prep_id,
                "interviewPrepId": interview_prep_id,
                "matchId": match_id,
                "userId": user_id,
                "analysisProvider": (
                    interview_item.get("provider")
                ),
                "sourceRegion": os.getenv(
                    "AWS_REGION",
                    "unknown",
                ),
                "submittedAt": utc_now(),
            },
        )


def process_job_match(
    *,
    identity: dict,
    item: dict,
    attempt_id: str,
    prior_status: str,
) -> str:
    match_id = identity["recordId"]

    if prior_status != STATUS_RESULT_READY:
        resume_analysis_id = item.get(
            "resumeAnalysisId"
        )
        job_description_text = str(
            item.get("jobDescriptionText") or ""
        ).strip()

        if not resume_analysis_id:
            raise ValueError(
                "No resumeAnalysisId found for "
                f"job match: {match_id}"
            )

        if not job_description_text:
            raise ValueError(
                "No jobDescriptionText found for "
                f"job match: {match_id}"
            )

        resume_item = get_item_strong(
            {
                "pk": user_pk(item["userId"]),
                "sk": resume_sk(resume_analysis_id),
            }
        )

        if not resume_item:
            raise ValueError(
                "Resume analysis not found: "
                f"{resume_analysis_id}"
            )

        resume_text = str(
            resume_item.get("resumeText") or ""
        ).strip()

        if not resume_text:
            raise ValueError(
                "No resumeText found for resume "
                f"analysis: {resume_analysis_id}"
            )

        requested_provider = (
            item.get("provider")
            or os.getenv(
                "ANALYSIS_PROVIDER",
                "rule-based",
            )
        )

        started = time.perf_counter()

        provider = get_analysis_provider(
            requested_provider
        )
        match_result = (
            provider.match_job_description(
                resume_text,
                job_description_text,
            )
        )

        duration_ms = int(
            (time.perf_counter() - started) * 1000
        )

        item = update_claimed_record(
            key=identity["key"],
            attempt_id=attempt_id,
            status=STATUS_RESULT_READY,
            fields={
                "provider": match_result["provider"],
                "model": match_result.get(
                    "model",
                    "",
                ),
                "analysisVersion": match_result[
                    "analysisVersion"
                ],
                "analysisDurationMs": duration_ms,
                "matchScore": match_result[
                    "matchScore"
                ],
                "leadershipMatchScore": (
                    match_result.get(
                        "leadershipMatchScore",
                        0,
                    )
                ),
                "technicalMatchScore": (
                    match_result.get(
                        "technicalMatchScore",
                        0,
                    )
                ),
                "architectureMatchScore": (
                    match_result.get(
                        "architectureMatchScore",
                        0,
                    )
                ),
                "atsKeywordScore": match_result.get(
                    "atsKeywordScore",
                    0,
                ),
                "matchedKeywords": match_result.get(
                    "matchedKeywords",
                    [],
                ),
                "missingKeywords": match_result.get(
                    "missingKeywords",
                    [],
                ),
                "leadershipGaps": match_result.get(
                    "leadershipGaps",
                    [],
                ),
                "technicalGaps": match_result.get(
                    "technicalGaps",
                    [],
                ),
                "recommendedResumeChanges": (
                    match_result.get(
                        "recommendedResumeChanges",
                        [],
                    )
                ),
                "executiveSummary": match_result.get(
                    "executiveSummary",
                    "",
                ),
                "resultReadyAt": utc_now(),
            },
        )

        claim = claim_job(identity)

        if claim["disposition"] != "CLAIMED":
            return attempt_id

        item = claim["item"]
        attempt_id = claim["attemptId"]

    dispatch_job_match_children(
        match_item=item,
    )

    update_claimed_record(
        key=identity["key"],
        attempt_id=attempt_id,
        status=STATUS_COMPLETED,
        fields={
            "completedAt": utc_now(),
        },
    )

    return attempt_id


def process_resume_tailoring(
    *,
    identity: dict,
    item: dict,
    attempt_id: str,
):
    tailoring_id = identity["recordId"]

    resume_text = str(
        item.get("resumeText") or ""
    ).strip()
    job_description_text = str(
        item.get("jobDescriptionText") or ""
    ).strip()

    if not resume_text:
        raise ValueError(
            f"No resumeText found for tailoring: "
            f"{tailoring_id}"
        )

    if not job_description_text:
        raise ValueError(
            "No jobDescriptionText found for "
            f"tailoring: {tailoring_id}"
        )

    requested_provider = (
        item.get("provider")
        or os.getenv(
            "ANALYSIS_PROVIDER",
            "rule-based",
        )
    )

    started = time.perf_counter()

    provider = get_analysis_provider(
        requested_provider
    )
    result = provider.tailor_resume(
        resume_text,
        job_description_text,
    )

    duration_ms = int(
        (time.perf_counter() - started) * 1000
    )

    update_claimed_record(
        key=identity["key"],
        attempt_id=attempt_id,
        status=STATUS_COMPLETED,
        fields={
            "provider": result["provider"],
            "model": result.get("model", ""),
            "analysisVersion": result[
                "analysisVersion"
            ],
            "analysisDurationMs": duration_ms,
            "tailoredExecutiveSummary": result.get(
                "tailoredExecutiveSummary",
                "",
            ),
            "tailoredResumeBullets": result.get(
                "tailoredResumeBullets",
                [],
            ),
            "keywordsToAdd": result.get(
                "keywordsToAdd",
                [],
            ),
            "rolePositioningAdvice": result.get(
                "rolePositioningAdvice",
                [],
            ),
            "atsOptimizationAdvice": result.get(
                "atsOptimizationAdvice",
                [],
            ),
            "rewriteWarnings": result.get(
                "rewriteWarnings",
                [],
            ),
            "completedAt": utc_now(),
        },
    )


def process_interview_preparation(
    *,
    identity: dict,
    item: dict,
    attempt_id: str,
):
    interview_prep_id = identity["recordId"]

    resume_text = str(
        item.get("resumeText") or ""
    ).strip()
    job_description_text = str(
        item.get("jobDescriptionText") or ""
    ).strip()

    if not resume_text:
        raise ValueError(
            "No resumeText found for interview "
            f"prep: {interview_prep_id}"
        )

    if not job_description_text:
        raise ValueError(
            "No jobDescriptionText found for "
            f"interview prep: {interview_prep_id}"
        )

    requested_provider = (
        item.get("provider")
        or os.getenv(
            "ANALYSIS_PROVIDER",
            "rule-based",
        )
    )

    started = time.perf_counter()

    provider = get_analysis_provider(
        requested_provider
    )
    result = provider.prepare_interview(
        resume_text,
        job_description_text,
    )

    duration_ms = int(
        (time.perf_counter() - started) * 1000
    )

    update_claimed_record(
        key=identity["key"],
        attempt_id=attempt_id,
        status=STATUS_COMPLETED,
        fields={
            "provider": result["provider"],
            "model": result.get("model", ""),
            "analysisVersion": result[
                "analysisVersion"
            ],
            "analysisDurationMs": duration_ms,
            "behavioralQuestions": result.get(
                "behavioralQuestions",
                [],
            ),
            "leadershipQuestions": result.get(
                "leadershipQuestions",
                [],
            ),
            "systemDesignQuestions": result.get(
                "systemDesignQuestions",
                [],
            ),
            "cloudArchitectureQuestions": result.get(
                "cloudArchitectureQuestions",
                [],
            ),
            "securityQuestions": result.get(
                "securityQuestions",
                [],
            ),
            "resumeSpecificQuestions": result.get(
                "resumeSpecificQuestions",
                [],
            ),
            "jobSpecificQuestions": result.get(
                "jobSpecificQuestions",
                [],
            ),
            "interviewReadinessSummary": result.get(
                "interviewReadinessSummary",
                "",
            ),
            "completedAt": utc_now(),
        },
    )


def process_record(record: dict):
    body = json.loads(record["body"])
    identity = derive_job_identity(body)

    claim = claim_job(identity)

    if claim["disposition"] == "SKIP":
        logger.info(
            "Skipping duplicate or already-processed job: "
            "jobType=%s recordId=%s status=%s",
            identity["jobType"],
            identity["recordId"],
            claim["item"].get("status"),
        )
        return

    item = claim["item"]
    attempt_id = claim["attemptId"]
    prior_status = claim["priorStatus"]

    logger.info(
        "Claimed worker job: "
        "jobType=%s recordId=%s attemptId=%s priorStatus=%s",
        identity["jobType"],
        identity["recordId"],
        attempt_id,
        prior_status,
    )

    try:
        if identity["jobType"] == "jobMatch":
            attempt_id = process_job_match(
                identity=identity,
                item=item,
                attempt_id=attempt_id,
                prior_status=prior_status,
            )

        elif identity["jobType"] == "resumeTailoring":
            process_resume_tailoring(
                identity=identity,
                item=item,
                attempt_id=attempt_id,
            )

        elif (
            identity["jobType"]
            == "interviewPreparation"
        ):
            process_interview_preparation(
                identity=identity,
                item=item,
                attempt_id=attempt_id,
            )

        else:
            process_resume_analysis(
                identity=identity,
                item=item,
                attempt_id=attempt_id,
            )

        logger.info(
            "Completed worker job: "
            "jobType=%s recordId=%s attemptId=%s",
            identity["jobType"],
            identity["recordId"],
            attempt_id,
        )

    except Exception as error:
        mark_claim_failed(
            key=identity["key"],
            attempt_id=attempt_id,
            error_message=str(error),
        )
        raise


def emit_worker_failure_metric(
    *,
    record: dict,
    message_id: str | None,
):
    """
    Emit a CloudWatch Embedded Metric Format record.

    Partial SQS batch failures do not necessarily increment the
    Lambda Errors metric because the handler returns successfully.
    This metric counts failed records rather than failed invocations.
    """
    job_type = "unknown"
    record_id = "unknown"

    try:
        body = json.loads(record.get("body") or "{}")
        job_type = body.get("jobType", "resumeAnalysis")
        record_id = str(
            body.get("jobId")
            or body.get("analysisId")
            or body.get("matchId")
            or body.get("tailoringId")
            or body.get("interviewPrepId")
            or "unknown"
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        pass

    metric_payload = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": (
                        f"{os.getenv('PROJECT_NAME', 'ai-resume-coach')}/"
                        f"{os.getenv('ENVIRONMENT', 'unknown')}"
                    ),
                    "Dimensions": [
                        ["FunctionName"],
                    ],
                    "Metrics": [
                        {
                            "Name": "WorkerRecordFailures",
                            "Unit": "Count",
                        },
                    ],
                },
            ],
        },
        "FunctionName": os.getenv(
            "AWS_LAMBDA_FUNCTION_NAME",
            "unknown",
        ),
        "WorkerRecordFailures": 1,
        "MessageId": message_id or "unknown",
        "JobType": job_type,
        "RecordId": record_id,
    }

    logger.error(json.dumps(metric_payload))


def lambda_handler(event, context):
    """
    Return an SQS partial-batch response.

    Successful and duplicate messages are acknowledged. Only failed
    message IDs are returned for retry.
    """
    failures = []

    for record in event.get("Records", []):
        message_id = record.get("messageId")

        try:
            process_record(record)

        except Exception:
            logger.exception(
                "Worker record processing failed: messageId=%s",
                message_id,
            )

            emit_worker_failure_metric(
                record=record,
                message_id=message_id,
            )

            if message_id:
                failures.append(
                    {
                        "itemIdentifier": message_id,
                    }
                )

    return {
        "batchItemFailures": failures,
    }
