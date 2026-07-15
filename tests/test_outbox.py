from __future__ import annotations

import pytest

from core.outbox import (
    OUTBOX_STATUS_PENDING,
    build_interview_preparation_outbox_event,
    build_job_match_outbox_event,
    build_outbox_event,
    build_resume_analysis_outbox_event,
    build_resume_tailoring_outbox_event,
    deterministic_event_id,
    payload_hash,
)


CREATED_AT = "2026-07-15T18:00:00+00:00"
REGION = "us-east-1"
REQUEST_ID = "request-123"
USER_ID = "user-123"


def test_deterministic_event_id_is_stable():
    first = deterministic_event_id(
        event_type="RESUME_ANALYSIS_REQUESTED",
        aggregate_type="resumeAnalysis",
        aggregate_id="analysis-123",
    )

    second = deterministic_event_id(
        event_type="RESUME_ANALYSIS_REQUESTED",
        aggregate_type="resumeAnalysis",
        aggregate_id="analysis-123",
    )

    assert first == second


def test_different_event_types_have_different_ids():
    analysis_event = deterministic_event_id(
        event_type="RESUME_ANALYSIS_REQUESTED",
        aggregate_type="resumeAnalysis",
        aggregate_id="same-id",
    )

    match_event = deterministic_event_id(
        event_type="JOB_MATCH_REQUESTED",
        aggregate_type="jobMatch",
        aggregate_id="same-id",
    )

    assert analysis_event != match_event


def test_payload_hash_ignores_dictionary_order():
    first = payload_hash(
        {
            "analysisId": "analysis-123",
            "userId": USER_ID,
        }
    )

    second = payload_hash(
        {
            "userId": USER_ID,
            "analysisId": "analysis-123",
        }
    )

    assert first == second


def test_build_outbox_event_creates_pending_item():
    event = build_outbox_event(
        event_type="TEST_REQUESTED",
        aggregate_type="testAggregate",
        aggregate_id="aggregate-123",
        job_type="testJob",
        payload={
            "jobType": "testJob",
            "jobId": "aggregate-123",
        },
        created_region=REGION,
        request_id=REQUEST_ID,
        created_at=CREATED_AT,
    )

    item = event.item

    assert item["pk"] == f"OUTBOX#{event.event_id}"
    assert item["sk"] == f"OUTBOX#{event.event_id}"
    assert item["recordType"] == "outboxEvent"
    assert item["eventId"] == event.event_id
    assert item["eventType"] == "TEST_REQUESTED"
    assert item["eventVersion"] == 1
    assert item["aggregateType"] == "testAggregate"
    assert item["aggregateId"] == "aggregate-123"
    assert item["jobType"] == "testJob"

    assert item["status"] == OUTBOX_STATUS_PENDING
    assert item["deliveryAttempts"] == 0
    assert item["version"] == 1

    assert item["createdAt"] == CREATED_AT
    assert item["updatedAt"] == CREATED_AT
    assert item["createdRegion"] == REGION
    assert item["lastUpdatedRegion"] == REGION
    assert item["createdByRequestId"] == REQUEST_ID
    assert item["updatedByRequestId"] == REQUEST_ID

    assert item["gsi1pk"] == "OUTBOX_STATUS#PENDING"
    assert item["gsi1sk"] == (
        f"{CREATED_AT}#{event.event_id}"
    )

    assert "expiresAt" not in item


def test_resume_analysis_event_matches_worker_contract():
    event = build_resume_analysis_outbox_event(
        analysis_id="analysis-123",
        user_id=USER_ID,
        analysis_provider="openai",
        created_region=REGION,
        request_id=REQUEST_ID,
        created_at=CREATED_AT,
    )

    assert event.item["jobType"] == "resumeAnalysis"
    assert event.item["payload"] == {
        "schemaVersion": 1,
        "jobType": "resumeAnalysis",
        "jobId": "analysis-123",
        "analysisId": "analysis-123",
        "userId": USER_ID,
        "analysisProvider": "openai",
        "sourceRegion": REGION,
    }


def test_job_match_event_matches_worker_contract():
    event = build_job_match_outbox_event(
        match_id="match-123",
        resume_analysis_id="analysis-123",
        user_id=USER_ID,
        analysis_provider="openai",
        created_region=REGION,
        request_id=REQUEST_ID,
        created_at=CREATED_AT,
    )

    payload = event.item["payload"]

    assert payload["schemaVersion"] == 1
    assert payload["jobType"] == "jobMatch"
    assert payload["jobId"] == "match-123"
    assert payload["matchId"] == "match-123"
    assert payload["analysisId"] == "analysis-123"
    assert payload["userId"] == USER_ID
    assert payload["analysisProvider"] == "openai"
    assert payload["sourceRegion"] == REGION


def test_tailoring_event_matches_worker_contract():
    event = build_resume_tailoring_outbox_event(
        tailoring_id="tailoring-123",
        match_id="match-123",
        user_id=USER_ID,
        analysis_provider="openai",
        created_region=REGION,
        request_id=REQUEST_ID,
        created_at=CREATED_AT,
    )

    payload = event.item["payload"]

    assert payload["schemaVersion"] == 1
    assert payload["jobType"] == "resumeTailoring"
    assert payload["jobId"] == "tailoring-123"
    assert payload["tailoringId"] == "tailoring-123"
    assert payload["matchId"] == "match-123"
    assert payload["userId"] == USER_ID
    assert payload["analysisProvider"] == "openai"
    assert payload["sourceRegion"] == REGION


def test_interview_event_matches_worker_contract():
    event = build_interview_preparation_outbox_event(
        interview_prep_id="interview-123",
        match_id="match-123",
        user_id=USER_ID,
        analysis_provider="openai",
        created_region=REGION,
        request_id=REQUEST_ID,
        created_at=CREATED_AT,
    )

    payload = event.item["payload"]

    assert payload["schemaVersion"] == 1
    assert payload["jobType"] == "interviewPreparation"
    assert payload["jobId"] == "interview-123"
    assert payload["interviewPrepId"] == "interview-123"
    assert payload["matchId"] == "match-123"
    assert payload["userId"] == USER_ID
    assert payload["analysisProvider"] == "openai"
    assert payload["sourceRegion"] == REGION


@pytest.mark.parametrize(
    "field_name,kwargs",
    [
        (
            "event_type",
            {
                "event_type": "",
                "aggregate_type": "type",
                "aggregate_id": "id",
            },
        ),
        (
            "aggregate_type",
            {
                "event_type": "EVENT",
                "aggregate_type": "",
                "aggregate_id": "id",
            },
        ),
        (
            "aggregate_id",
            {
                "event_type": "EVENT",
                "aggregate_type": "type",
                "aggregate_id": "",
            },
        ),
    ],
)
def test_deterministic_event_id_requires_identity_fields(
    field_name,
    kwargs,
):
    with pytest.raises(
        ValueError,
        match=f"{field_name} is required",
    ):
        deterministic_event_id(**kwargs)
