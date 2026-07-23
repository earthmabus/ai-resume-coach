from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from core.retry_policy import decide_retry, receive_attempt
from core.workflow_state import (
    STATUS_PROCESSING,
    STATUS_QUEUED,
    STATUS_QUEUED_PENDING_DISPATCH,
    STATUS_WAITING,
    can_transition,
    assert_transition,
    known_status,
)
from core.terminal_failure import TerminalFailureEnvelope
from providers.factory import get_analysis_provider

AWS_REGION = os.getenv("AWS_REGION", "unknown")
DEPLOYMENT_ID = os.getenv("DEPLOYMENT_ID", "unknown")
ENVIRONMENT = os.getenv("ENVIRONMENT", "unknown")
GSI1_INDEX_NAME = "gsi1"
GSI1_PARTITION_KEY = "gsi1pk"


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("RESUME_ANALYSIS_TABLE"))

sqs = boto3.client("sqs")
queue_url = os.getenv("RESUME_ANALYSIS_QUEUE_URL")
terminal_failure_queue_url = os.getenv("TERMINAL_FAILURE_QUEUE_URL")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


STATUS_COMPLETED = "completed"
STATUS_FAILED_RETRYABLE = "FAILED_RETRYABLE"
STATUS_FAILED_PERMANENT = "FAILED_PERMANENT"
STATUS_FAILED_RETRY_EXHAUSTED = "FAILED_RETRY_EXHAUSTED"
STATUS_WORKER_PROCESSING = "WORKER_PROCESSING"
STATUS_RESULT_READY = "RESULT_READY_PENDING_CHILD_DISPATCH"

DEFAULT_LEASE_SECONDS = int(
    os.getenv("WORKER_PROCESSING_LEASE_SECONDS", "300")
)
DEFAULT_MAX_PROCESSING_ATTEMPTS = int(
    os.getenv("WORKER_MAX_PROCESSING_ATTEMPTS", "5")
)


@dataclass(frozen=True)
class WorkerMessageContext:
    request_id: str
    correlation_id: str
    work_id: str
    outbox_event_id: str
    transport_message_id: str
    runtime_invocation_id: str
    current_region: str
    owner_region: str
    source_region: str
    event_type: str
    job_type: str

    def as_log_fields(self) -> dict[str, str]:
        return {
            "service": "resume-analysis",
            "component": "worker",
            "requestId": self.request_id,
            "correlationId": self.correlation_id,
            "workId": self.work_id,
            "outboxEventId": self.outbox_event_id,
            "transportMessageId": self.transport_message_id,
            "runtimeInvocationId": self.runtime_invocation_id,
            "currentRegion": self.current_region,
            "ownerRegion": self.owner_region,
            "sourceRegion": self.source_region,
            "eventType": self.event_type,
            "jobType": self.job_type,
            "deploymentId": DEPLOYMENT_ID,
        }


def work_id_from_body(body: dict[str, Any]) -> str:
    return str(
        body.get("jobId")
        or body.get("analysisId")
        or body.get("matchId")
        or body.get("tailoringId")
        or body.get("interviewPrepId")
        or ""
    )


def build_worker_message_context(
    *,
    record: dict[str, Any],
    body: dict[str, Any],
    runtime_invocation_id: str | None = None,
) -> WorkerMessageContext:
    request_id = str(
        body.get("requestId")
        or body.get("createdByRequestId")
        or ""
    )
    correlation_id = str(
        body.get("correlationId")
        or request_id
        or ""
    )

    return WorkerMessageContext(
        request_id=request_id,
        correlation_id=correlation_id,
        work_id=work_id_from_body(body),
        outbox_event_id=str(body.get("outboxEventId") or ""),
        transport_message_id=str(record.get("messageId") or ""),
        runtime_invocation_id=str(runtime_invocation_id or ""),
        current_region=AWS_REGION,
        owner_region=str(body.get("ownerRegion") or ""),
        source_region=str(body.get("sourceRegion") or ""),
        event_type=str(body.get("eventType") or ""),
        job_type=str(body.get("jobType") or "resumeAnalysis"),
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
        IndexName=GSI1_INDEX_NAME,
        KeyConditionExpression=Key(GSI1_PARTITION_KEY).eq(
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
    """Return statuses this worker may atomically claim for ``job_type``.

    The authoritative workflow matrix owns the normal transition into
    ``WORKER_PROCESSING``. Job-specific filtering prevents states that are
    valid for one workflow (for example WAITING or RESULT_READY) from being
    claimed by another workflow.
    """
    candidates = {
        status
        for status in (
            STATUS_PROCESSING,
            STATUS_QUEUED_PENDING_DISPATCH,
            STATUS_QUEUED,
            STATUS_FAILED_RETRYABLE,
            STATUS_WAITING,
            STATUS_RESULT_READY,
        )
        if can_transition(status, STATUS_WORKER_PROCESSING)
    }

    if job_type not in {
        "resumeTailoring",
        "interviewPreparation",
    }:
        candidates.discard(STATUS_WAITING)

    if job_type != "jobMatch":
        candidates.discard(STATUS_RESULT_READY)

    return candidates


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

    if current_status in {
        STATUS_FAILED_PERMANENT,
        STATUS_FAILED_RETRY_EXHAUSTED,
    }:
        if not item.get("terminalFailurePublished", False):
            return {
                "disposition": "TERMINAL_FAILURE_PENDING",
                "item": item,
                "attemptId": None,
                "priorStatus": current_status,
            }
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

    else:
        allowed_statuses = claimable_statuses(job_type)
        if current_status not in allowed_statuses:
            raise RuntimeError(
                f"{identity['recordType']} is not claimable "
                f"from status {current_status!r}; "
                f"jobType={job_type!r}; "
                f"claimableStatuses={sorted(allowed_statuses)!r}"
            )

    assert_transition(str(current_status or ""), STATUS_WORKER_PROCESSING)

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
    assert_transition(STATUS_WORKER_PROCESSING, status)

    names = {
        "#status": "status",
        "#version": "version",
    }

    values = {
        ":status": status,
        ":attemptId": attempt_id,
        ":updatedAt": utc_now(),
        ":region": AWS_REGION,
        ":deploymentId": DEPLOYMENT_ID,
        ":zero": 0,
        ":one": 1,
    }

    assignments = [
        "#status = :status",
        "updatedAt = :updatedAt",
        "lastUpdatedRegion = :region, "
        "lastUpdatedByDeploymentId = :deploymentId",
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
    failure_category: str = "TRANSIENT_INFRASTRUCTURE",
    retryable: bool = True,
    exhausted: bool = False,
    processing_attempt: int = 1,
    error_type: str = "Exception",
):
    if exhausted:
        status = STATUS_FAILED_RETRY_EXHAUSTED
    elif retryable:
        status = STATUS_FAILED_RETRYABLE
    else:
        status = STATUS_FAILED_PERMANENT

    try:
        return update_claimed_record(
            key=key,
            attempt_id=attempt_id,
            status=status,
            fields={
                "errorMessage": error_message[:2000],
                "errorType": error_type,
                "failureCategory": failure_category,
                "failureRetryable": retryable,
                "processingAttempt": processing_attempt,
                "processingAttemptsExhausted": exhausted,
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



def publish_terminal_failure(
    *,
    identity: dict,
    message_context: WorkerMessageContext,
    item: dict,
) -> str:
    if not terminal_failure_queue_url:
        raise RuntimeError("TERMINAL_FAILURE_QUEUE_URL is not configured")

    failure_id = str(item.get("terminalFailureId") or uuid.uuid4())
    envelope = TerminalFailureEnvelope(
        failure_id=failure_id,
        work_id=identity["recordId"],
        job_type=identity["jobType"],
        record_type=identity["recordType"],
        status=str(item.get("status") or STATUS_FAILED_PERMANENT),
        failure_category=str(item.get("failureCategory") or "PERMANENT"),
        processing_attempt=int(item.get("processingAttempt", 1)),
        max_processing_attempts=DEFAULT_MAX_PROCESSING_ATTEMPTS,
        error_type=str(item.get("errorType") or "Exception"),
        error_message=str(item.get("errorMessage") or "Workflow failed"),
        request_id=message_context.request_id,
        correlation_id=message_context.correlation_id,
        outbox_event_id=message_context.outbox_event_id,
        owner_region=message_context.owner_region,
        source_region=message_context.source_region,
        failed_region=AWS_REGION,
        deployment_id=DEPLOYMENT_ID,
        failed_at=str(item.get("failedAt") or utc_now()),
    )
    sqs.send_message(
        QueueUrl=terminal_failure_queue_url,
        MessageBody=envelope.to_json(),
    )
    return failure_id


def mark_terminal_failure_published(*, key: dict, failure_id: str) -> None:
    table.update_item(
        Key=key,
        UpdateExpression=(
            "SET terminalFailurePublished = :published, "
            "terminalFailureId = :failureId, "
            "terminalFailurePublishedAt = :publishedAt, "
            "updatedAt = :updatedAt"
        ),
        ConditionExpression=(
            "#status IN (:permanent, :exhausted) "
            "AND (attribute_not_exists(terminalFailurePublished) "
            "OR terminalFailurePublished = :notPublished)"
        ),
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":published": True,
            ":notPublished": False,
            ":failureId": failure_id,
            ":publishedAt": utc_now(),
            ":updatedAt": utc_now(),
            ":permanent": STATUS_FAILED_PERMANENT,
            ":exhausted": STATUS_FAILED_RETRY_EXHAUSTED,
        },
    )

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
            "processedAt": utc_now(),
            "processedRegion": AWS_REGION,
            "processedByDeploymentId": DEPLOYMENT_ID,
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
    request_id = str(
        match_item.get("createdByRequestId") or ""
    )
    correlation_id = str(
        match_item.get("correlationId")
        or request_id
        or ""
    )
    owner_region = str(
        match_item.get("ownerRegion")
        or match_item.get("createdRegion")
        or AWS_REGION
    )
    source_region = str(
        match_item.get("createdRegion")
        or AWS_REGION
    )
    source_deployment_id = str(
        match_item.get("createdByDeploymentId")
        or DEPLOYMENT_ID
    )

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
                "requestId": request_id,
                "correlationId": correlation_id,
                "ownerRegion": owner_region,
                "analysisProvider": (
                    tailoring_item.get("provider")
                ),
                "sourceRegion": source_region,
                "sourceDeploymentId": source_deployment_id,
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
                "requestId": request_id,
                "correlationId": correlation_id,
                "ownerRegion": owner_region,
                "analysisProvider": (
                    interview_item.get("provider")
                ),
                "sourceRegion": source_region,
                "sourceDeploymentId": source_deployment_id,
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
            "processedAt": utc_now(),
            "processedRegion": AWS_REGION,
            "processedByDeploymentId": DEPLOYMENT_ID,
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
            "processedAt": utc_now(),
            "processedRegion": AWS_REGION,
            "processedByDeploymentId": DEPLOYMENT_ID,
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
            "processedAt": utc_now(),
            "processedRegion": AWS_REGION,
            "processedByDeploymentId": DEPLOYMENT_ID,
        },
    )


def process_record(
    record: dict,
    *,
    runtime_invocation_id: str | None = None,
):
    body = json.loads(record["body"])
    message_context = build_worker_message_context(
        record=record,
        body=body,
        runtime_invocation_id=runtime_invocation_id,
    )
    identity = derive_job_identity(body)

    claim = claim_job(identity)

    if claim["disposition"] == "TERMINAL_FAILURE_PENDING":
        failure_id = publish_terminal_failure(
            identity=identity,
            message_context=message_context,
            item=claim["item"],
        )
        mark_terminal_failure_published(
            key=identity["key"],
            failure_id=failure_id,
        )
        return

    if claim["disposition"] == "SKIP":
        logger.info(
            json.dumps(
                {
                    **message_context.as_log_fields(),
                    "operation": "worker-process",
                    "result": "SKIPPED",
                    "message": (
                        "Skipping duplicate or already-processed job"
                    ),
                    "recordId": identity["recordId"],
                    "priorStatus": claim["item"].get("status"),
                },
                separators=(",", ":"),
            )
        )
        return

    item = claim["item"]
    attempt_id = claim["attemptId"]
    prior_status = claim["priorStatus"]

    logger.info(
        json.dumps(
            {
                **message_context.as_log_fields(),
                "operation": "worker-claim",
                "result": "CLAIMED",
                "message": "Claimed worker job",
                "recordId": identity["recordId"],
                "processingAttemptId": attempt_id,
                "priorStatus": prior_status,
            },
            separators=(",", ":"),
        )
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
            json.dumps(
                {
                    **message_context.as_log_fields(),
                    "operation": "worker-process",
                    "result": "SUCCESS",
                    "message": "Completed worker job",
                    "recordId": identity["recordId"],
                    "processingAttemptId": attempt_id,
                },
                separators=(",", ":"),
            )
        )

    except Exception as error:
        processing_attempt = receive_attempt(record)
        decision = decide_retry(
            error,
            attempt=processing_attempt,
            max_attempts=DEFAULT_MAX_PROCESSING_ATTEMPTS,
        )
        failure_item = mark_claim_failed(
            key=identity["key"],
            attempt_id=attempt_id,
            error_message=str(error),
            failure_category=decision.category.value,
            retryable=decision.retryable,
            exhausted=decision.exhausted,
            processing_attempt=decision.attempt,
            error_type=type(error).__name__,
        )
        if decision.terminal and failure_item is not None:
            failure_id = publish_terminal_failure(
                identity=identity,
                message_context=message_context,
                item=failure_item,
            )
            mark_terminal_failure_published(
                key=identity["key"],
                failure_id=failure_id,
            )
        logger.error(
            json.dumps(
                {
                    **message_context.as_log_fields(),
                    "operation": "worker-process",
                    "result": "FAILURE",
                    "message": "Worker job failed",
                    "recordId": identity["recordId"],
                    "processingAttemptId": attempt_id,
                    "processingAttempt": decision.attempt,
                    "maxProcessingAttempts": decision.max_attempts,
                    "failureCategory": decision.category.value,
                    "failureRetryable": decision.retryable,
                    "processingAttemptsExhausted": decision.exhausted,
                    "errorType": type(error).__name__,
                },
                separators=(",", ":"),
            )
        )
        if not decision.terminal:
            raise


def emit_worker_failure_metric(
    *,
    record: dict,
    message_id: str | None,
    runtime_invocation_id: str | None = None,
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
        request_id = str(
            body.get("requestId")
            or body.get("createdByRequestId")
            or ""
        )
        correlation_id = str(
            body.get("correlationId")
            or request_id
            or ""
        )
        outbox_event_id = str(
            body.get("outboxEventId") or ""
        )
        owner_region = str(body.get("ownerRegion") or "")
        source_region = str(body.get("sourceRegion") or "")
        event_type = str(body.get("eventType") or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        request_id = ""
        correlation_id = ""
        outbox_event_id = ""
        owner_region = ""
        source_region = ""
        event_type = ""

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
        "RequestId": request_id,
        "CorrelationId": correlation_id,
        "OutboxEventId": outbox_event_id,
        "OwnerRegion": owner_region,
        "SourceRegion": source_region,
        "CurrentRegion": AWS_REGION,
        "EventType": event_type,
        "RuntimeInvocationId": runtime_invocation_id or "",
    }

    logger.error(json.dumps(metric_payload))


def lambda_handler(event, context):
    runtime_invocation_id = getattr(
        context,
        "aws_request_id",
        None,
    )
    logger.info(
        json.dumps(
            {
                "service": "resume-analysis",
                "component": "worker",
                "operation": "worker-invocation",
                "result": "STARTED",
                "message": "Worker invocation started",
                "region": AWS_REGION,
                "currentRegion": AWS_REGION,
                "deploymentId": DEPLOYMENT_ID,
                "environment": ENVIRONMENT,
                "recordCount": len(event.get("Records", [])),
                "runtimeInvocationId": runtime_invocation_id,
                "awsRequestId": runtime_invocation_id,
            },
            separators=(",", ":"),
        )
    )
    """
    Return an SQS partial-batch response.

    Successful and duplicate messages are acknowledged. Only failed
    message IDs are returned for retry.
    """
    failures = []

    for record in event.get("Records", []):
        message_id = record.get("messageId")

        try:
            process_record(
                record,
                runtime_invocation_id=runtime_invocation_id,
            )

        except Exception:
            logger.exception(
                "Worker record processing failed: messageId=%s",
                message_id,
            )

            emit_worker_failure_metric(
                record=record,
                message_id=message_id,
                runtime_invocation_id=runtime_invocation_id,
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
