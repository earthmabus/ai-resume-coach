from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from core.config import get_config
from core.keys import (
    outbox_pk,
    outbox_sk,
    outbox_status_pk,
    outbox_status_sk,
)


OUTBOX_STATUS_PENDING = "PENDING"
OUTBOX_STATUS_DISPATCHING = "DISPATCHING"
OUTBOX_STATUS_DELIVERED = "DELIVERED"
OUTBOX_STATUS_FAILED_RETRYABLE = "FAILED_RETRYABLE"
OUTBOX_STATUS_FAILED_PERMANENT = "FAILED_PERMANENT"

SUPPORTED_OUTBOX_STATUSES = {
    OUTBOX_STATUS_PENDING,
    OUTBOX_STATUS_DISPATCHING,
    OUTBOX_STATUS_DELIVERED,
    OUTBOX_STATUS_FAILED_RETRYABLE,
    OUTBOX_STATUS_FAILED_PERMANENT,
}

OUTBOX_EVENT_VERSION = 1


@dataclass(frozen=True)
class OutboxEvent:
    event_id: str
    item: dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Mapping[str, Any]) -> str:
    """
    Produce stable JSON for fingerprints and deterministic identifiers.
    """
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def deterministic_event_id(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
) -> str:
    """
    Return the same event ID for the same logical dispatch.

    Do not include region, request ID, timestamp, or retry count. Those
    values would make retries produce different outbox events.
    """
    normalized_event_type = str(event_type or "").strip()
    normalized_aggregate_type = str(
        aggregate_type or ""
    ).strip()
    normalized_aggregate_id = str(
        aggregate_id or ""
    ).strip()

    if not normalized_event_type:
        raise ValueError("event_type is required")

    if not normalized_aggregate_type:
        raise ValueError("aggregate_type is required")

    if not normalized_aggregate_id:
        raise ValueError("aggregate_id is required")

    identity = canonical_json(
        {
            "eventType": normalized_event_type,
            "aggregateType": normalized_aggregate_type,
            "aggregateId": normalized_aggregate_id,
            "eventVersion": OUTBOX_EVENT_VERSION,
        }
    )

    return hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()


def payload_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def build_outbox_event(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    job_type: str,
    payload: Mapping[str, Any],
    created_region: str,
    request_id: str,
    created_deployment_id: str | None = None,
    created_at: str | None = None,
) -> OutboxEvent:
    """
    Build a PENDING outbox event.

    Pending events are immediately dispatchable and therefore do not
    contain nextDeliveryAttemptAt. That field is introduced only after
    a failed delivery schedules a retry.

    The item intentionally has no TTL while it is pending. An undelivered
    event must never disappear because a retention period elapsed.
    A TTL may be added only after it reaches DELIVERED.
    """
    normalized_job_type = str(job_type or "").strip()
    normalized_region = str(created_region or "").strip()
    normalized_request_id = str(request_id or "").strip()
    normalized_deployment_id = str(
        created_deployment_id
        or get_config().deployment_id
        or "unknown"
    ).strip()

    if not normalized_job_type:
        raise ValueError("job_type is required")

    if not normalized_region:
        raise ValueError("created_region is required")

    if not normalized_request_id:
        raise ValueError("request_id is required")

    if not isinstance(payload, Mapping):
        raise ValueError("payload must be a mapping")

    event_id = deterministic_event_id(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
    )

    timestamp = created_at or utc_now()
    normalized_payload = dict(payload)

    item = {
        "pk": outbox_pk(event_id),
        "sk": outbox_sk(event_id),
        "recordType": "outboxEvent",
        "eventId": event_id,
        "eventType": event_type,
        "eventVersion": OUTBOX_EVENT_VERSION,
        "aggregateType": aggregate_type,
        "aggregateId": aggregate_id,
        "jobType": normalized_job_type,
        "payload": normalized_payload,
        "payloadHash": payload_hash(normalized_payload),
        "status": OUTBOX_STATUS_PENDING,
        "createdAt": timestamp,
        "updatedAt": timestamp,
        "createdRegion": normalized_region,
        "createdByDeploymentId": normalized_deployment_id,
        "lastUpdatedRegion": normalized_region,
        "lastUpdatedByDeploymentId": normalized_deployment_id,
        "createdByRequestId": normalized_request_id,
        "updatedByRequestId": normalized_request_id,
        "deliveryAttempts": 0,
        "version": 1,

        # Reuse the table's existing sparse GSI to retrieve outbox events
        # by status and original creation order. Retry eligibility is
        # stored separately in nextDeliveryAttemptAt.
        #
        # These attributes should be removed when the event reaches
        # DELIVERED so delivered events no longer appear in the GSI.
        "gsi1pk": outbox_status_pk(
            OUTBOX_STATUS_PENDING
        ),
        "gsi1sk": outbox_status_sk(
            created_at=timestamp,
            event_id=event_id,
        ),
    }

    return OutboxEvent(
        event_id=event_id,
        item=item,
    )


def build_resume_analysis_outbox_event(
    *,
    analysis_id: str,
    user_id: str,
    analysis_provider: str,
    created_region: str,
    request_id: str,
    created_deployment_id: str | None = None,
    created_at: str | None = None,
) -> OutboxEvent:
    return build_outbox_event(
        event_type="RESUME_ANALYSIS_REQUESTED",
        aggregate_type="resumeAnalysis",
        aggregate_id=analysis_id,
        job_type="resumeAnalysis",
        payload={
            "schemaVersion": 1,
            "jobType": "resumeAnalysis",
            "jobId": analysis_id,
            "analysisId": analysis_id,
            "userId": user_id,
            "analysisProvider": analysis_provider,
            "sourceRegion": created_region,
        },
        created_region=created_region,
        request_id=request_id,
        created_deployment_id=created_deployment_id,
        created_at=created_at,
    )


def build_job_match_outbox_event(
    *,
    match_id: str,
    resume_analysis_id: str,
    user_id: str,
    analysis_provider: str,
    created_region: str,
    request_id: str,
    created_deployment_id: str | None = None,
    created_at: str | None = None,
) -> OutboxEvent:
    return build_outbox_event(
        event_type="JOB_MATCH_REQUESTED",
        aggregate_type="jobMatch",
        aggregate_id=match_id,
        job_type="jobMatch",
        payload={
            "schemaVersion": 1,
            "jobType": "jobMatch",
            "jobId": match_id,
            "matchId": match_id,
            "analysisId": resume_analysis_id,
            "userId": user_id,
            "analysisProvider": analysis_provider,
            "sourceRegion": created_region,
        },
        created_region=created_region,
        request_id=request_id,
        created_deployment_id=created_deployment_id,
        created_at=created_at,
    )


def build_resume_tailoring_outbox_event(
    *,
    tailoring_id: str,
    match_id: str,
    user_id: str,
    analysis_provider: str,
    created_region: str,
    request_id: str,
    created_deployment_id: str | None = None,
    created_at: str | None = None,
) -> OutboxEvent:
    return build_outbox_event(
        event_type="RESUME_TAILORING_REQUESTED",
        aggregate_type="resumeTailoring",
        aggregate_id=tailoring_id,
        job_type="resumeTailoring",
        payload={
            "schemaVersion": 1,
            "jobType": "resumeTailoring",
            "jobId": tailoring_id,
            "tailoringId": tailoring_id,
            "matchId": match_id,
            "userId": user_id,
            "analysisProvider": analysis_provider,
            "sourceRegion": created_region,
        },
        created_region=created_region,
        request_id=request_id,
        created_deployment_id=created_deployment_id,
        created_at=created_at,
    )


def build_interview_preparation_outbox_event(
    *,
    interview_prep_id: str,
    match_id: str,
    user_id: str,
    analysis_provider: str,
    created_region: str,
    request_id: str,
    created_deployment_id: str | None = None,
    created_at: str | None = None,
) -> OutboxEvent:
    return build_outbox_event(
        event_type="INTERVIEW_PREPARATION_REQUESTED",
        aggregate_type="interviewPreparation",
        aggregate_id=interview_prep_id,
        job_type="interviewPreparation",
        payload={
            "schemaVersion": 1,
            "jobType": "interviewPreparation",
            "jobId": interview_prep_id,
            "interviewPrepId": interview_prep_id,
            "matchId": match_id,
            "userId": user_id,
            "analysisProvider": analysis_provider,
            "sourceRegion": created_region,
        },
        created_region=created_region,
        request_id=request_id,
        created_deployment_id=created_deployment_id,
        created_at=created_at,
    )
