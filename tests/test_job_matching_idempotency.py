from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core.errors import IdempotencyKeyRequiredError
from core.idempotency import (
    DISPOSITION_REPLAY_COMPLETED,
    DISPOSITION_REPLAY_IN_PROGRESS,
    DISPOSITION_RESERVED,
    IdempotencyReservation,
)
from features import job_matching


IDEMPOTENCY_KEY = "12345678-1234-1234-1234-123456789012"
USER_ID = "user-123"
REQUEST_ID = "request-123"
CORRELATION_ID = "correlation-123"
REQUEST_HASH = "request-hash-123"

ANALYSIS_ID = "analysis-123"
MATCH_ID = "11111111-1111-4111-8111-111111111111"

TAILORING_ID = job_matching.stable_child_id(
    match_id=MATCH_ID,
    child_type="resume-tailoring",
)
INTERVIEW_PREP_ID = job_matching.stable_child_id(
    match_id=MATCH_ID,
    child_type="interview-preparation",
)


def make_event(
    *,
    idempotency_key: str | None = IDEMPOTENCY_KEY,
    body: dict | None = None,
) -> dict:
    headers = {
        "Content-Type": "application/json",
        "X-Correlation-Id": CORRELATION_ID,
    }

    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key

    payload = body or {
        "analysisId": ANALYSIS_ID,
        "jobName": "Director of Software Engineering",
        "jobUrl": "https://example.com/jobs/123",
        "jobDescriptionText": (
            "Lead software engineering, cloud, and security teams."
        ),
        "analysisProvider": "rule-based",
    }

    return {
        "routeKey": "POST /match-job-description",
        "headers": headers,
        "body": json.dumps(payload),
        "requestContext": {
            "requestId": REQUEST_ID,
            "routeKey": "POST /match-job-description",
            "http": {
                "method": "POST",
                "path": "/match-job-description",
            },
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": USER_ID,
                    }
                }
            },
        },
    }


def response_body(response: dict) -> dict:
    return json.loads(response["body"])


@pytest.fixture
def dependencies(monkeypatch):
    resume_item = {
        "pk": f"USER#{USER_ID}",
        "sk": f"RESUME#{ANALYSIS_ID}",
        "recordType": "resumeAnalysis",
        "userId": USER_ID,
        "analysisId": ANALYSIS_ID,
        "status": "completed",
        "resumeName": "Engineering Resume",
        "resumeText": "Experienced engineering leader.",
        "sourceType": "pdf",
        "score": 91,
        "createdAt": "2026-07-15T00:00:00+00:00",
        "fileName": "resume.pdf",
        "documentBucket": "test-bucket",
        "documentKey": "uploads/resume.pdf",
    }

    table = MagicMock()

    def get_item(*, Key, ConsistentRead):
        if Key["sk"] == f"RESUME#{ANALYSIS_ID}":
            return {"Item": resume_item}

        if Key["sk"] == f"MATCH#{MATCH_ID}":
            return {}

        return {}

    table.get_item.side_effect = get_item

    table.update_item.return_value = {
        "Attributes": {
            "matchId": MATCH_ID,
            "status": "processing",
            "version": 2,
            "jobName": "Director of Software Engineering",
            "jobUrl": "https://example.com/jobs/123",
            "createdAt": "2026-07-15T00:00:00+00:00",
        }
    }


    reserve_request = MagicMock(
        return_value=IdempotencyReservation(
            disposition=DISPOSITION_RESERVED,
            resource_id=MATCH_ID,
        )
    )

    put_item_if_absent = MagicMock(return_value=True)
    put_items_and_outbox_if_absent = MagicMock(return_value=True)
    complete_request = MagicMock()
    mark_request_retryable = MagicMock()
    request_fingerprint = MagicMock(return_value=REQUEST_HASH)

    monkeypatch.setattr(job_matching, "table", table)
    monkeypatch.setattr(
        job_matching,
        "reserve_request",
        reserve_request,
    )
    monkeypatch.setattr(
        job_matching,
        "put_item_if_absent",
        put_item_if_absent,
    )
    monkeypatch.setattr(
        job_matching,
        "put_items_and_outbox_if_absent",
        put_items_and_outbox_if_absent,
    )
    monkeypatch.setattr(
        job_matching,
        "complete_request",
        complete_request,
    )
    monkeypatch.setattr(
        job_matching,
        "mark_request_retryable",
        mark_request_retryable,
    )
    monkeypatch.setattr(
        job_matching,
        "request_fingerprint",
        request_fingerprint,
    )

    return SimpleNamespace(
        resume_item=resume_item,
        table=table,
        reserve_request=reserve_request,
        put_item_if_absent=put_item_if_absent,
        put_items_and_outbox_if_absent=(
            put_items_and_outbox_if_absent
        ),
        complete_request=complete_request,
        mark_request_retryable=mark_request_retryable,
        request_fingerprint=request_fingerprint,
    )


def test_stable_child_ids_are_deterministic():
    first_tailoring_id = job_matching.stable_child_id(
        match_id=MATCH_ID,
        child_type="resume-tailoring",
    )
    second_tailoring_id = job_matching.stable_child_id(
        match_id=MATCH_ID,
        child_type="resume-tailoring",
    )

    first_interview_id = job_matching.stable_child_id(
        match_id=MATCH_ID,
        child_type="interview-preparation",
    )

    assert first_tailoring_id == second_tailoring_id
    assert first_tailoring_id != first_interview_id


def test_missing_idempotency_key_is_rejected(dependencies):
    with pytest.raises(IdempotencyKeyRequiredError):
        job_matching.match_job_description(
            make_event(idempotency_key=None)
        )

    dependencies.reserve_request.assert_not_called()


def test_missing_analysis_id_returns_400(dependencies):
    response = job_matching.match_job_description(
        make_event(
            body={
                "analysisId": "",
                "jobName": "Director",
                "jobDescriptionText": "Description",
            }
        )
    )

    assert response["statusCode"] == 400
    assert response_body(response) == {
        "error": "analysisId is required"
    }

    dependencies.reserve_request.assert_not_called()


def test_missing_job_description_returns_400(dependencies):
    response = job_matching.match_job_description(
        make_event(
            body={
                "analysisId": ANALYSIS_ID,
                "jobName": "Director",
                "jobDescriptionText": "",
            }
        )
    )

    assert response["statusCode"] == 400
    assert response_body(response) == {
        "error": "jobDescriptionText is required"
    }

    dependencies.reserve_request.assert_not_called()


def test_resume_is_read_by_authoritative_base_key(
    dependencies,
):
    response = job_matching.match_job_description(make_event())

    assert response["statusCode"] == 202

    dependencies.table.get_item.assert_any_call(
        Key={
            "pk": f"USER#{USER_ID}",
            "sk": f"RESUME#{ANALYSIS_ID}",
        },
        ConsistentRead=True,
    )


def test_first_request_creates_match_and_children(
    dependencies,
):
    response = job_matching.match_job_description(make_event())
    body = response_body(response)

    assert response["statusCode"] == 202
    assert body["matchId"] == MATCH_ID
    assert body["tailoringId"] == TAILORING_ID
    assert body["interviewPrepId"] == INTERVIEW_PREP_ID
    assert body["status"] == "QUEUED_PENDING_DISPATCH"
    assert body["version"] == 1

    dependencies.put_items_and_outbox_if_absent.assert_called_once()
    dependencies.put_item_if_absent.assert_not_called()
    dependencies.table.update_item.assert_not_called()
    dependencies.complete_request.assert_called_once()

    transaction = (
        dependencies.put_items_and_outbox_if_absent.call_args.kwargs
    )
    created_items = transaction["items"]
    outbox_item = transaction["outbox_item"]

    match_item = next(
        item for item in created_items
        if item["recordType"] == "jobMatch"
    )
    tailoring_item = next(
        item for item in created_items
        if item["recordType"] == "resumeTailoring"
    )
    interview_item = next(
        item for item in created_items
        if item["recordType"] == "interviewPreparation"
    )

    assert match_item["status"] == "QUEUED_PENDING_DISPATCH"
    assert match_item["version"] == 1
    assert match_item["correlationId"] == CORRELATION_ID
    assert tailoring_item["status"] == "waiting"
    assert tailoring_item["correlationId"] == CORRELATION_ID
    assert interview_item["status"] == "waiting"
    assert interview_item["correlationId"] == CORRELATION_ID

    assert outbox_item["eventType"] == "JOB_MATCH_REQUESTED"
    assert outbox_item["aggregateId"] == MATCH_ID
    assert outbox_item["status"] == "PENDING"
    assert outbox_item["correlationId"] == CORRELATION_ID
    assert outbox_item["payload"]["requestId"] == REQUEST_ID
    assert outbox_item["payload"]["correlationId"] == CORRELATION_ID

    completion = dependencies.complete_request.call_args.kwargs
    assert completion["response_body"]["status"] == (
        "QUEUED_PENDING_DISPATCH"
    )


def test_retry_preserves_original_correlation_on_created_work(
    dependencies,
):
    dependencies.reserve_request.return_value = IdempotencyReservation(
        disposition=DISPOSITION_RESERVED,
        resource_id=MATCH_ID,
        correlation_id="original-correlation",
    )

    response = job_matching.match_job_description(make_event())

    assert response["statusCode"] == 202

    transaction = (
        dependencies.put_items_and_outbox_if_absent.call_args.kwargs
    )
    match_item = next(
        item for item in transaction["items"]
        if item["recordType"] == "jobMatch"
    )
    outbox_item = transaction["outbox_item"]

    assert match_item["correlationId"] == "original-correlation"
    assert outbox_item["correlationId"] == "original-correlation"
    assert (
        outbox_item["payload"]["correlationId"]
        == "original-correlation"
    )


def test_outbox_payload_preserves_worker_contract(
    dependencies,
):
    job_matching.match_job_description(make_event())

    outbox_item = (
        dependencies.put_items_and_outbox_if_absent
        .call_args.kwargs["outbox_item"]
    )
    message = outbox_item["payload"]

    assert message["jobType"] == "jobMatch"
    assert message["matchId"] == MATCH_ID
    assert message["analysisId"] == ANALYSIS_ID
    assert message["jobId"] == MATCH_ID
    assert message["userId"] == USER_ID
    assert message["sourceRegion"] == "us-east-1"


def test_completed_replay_does_not_repeat_work(
    dependencies,
):
    stored_body = {
        "matchId": MATCH_ID,
        "analysisId": MATCH_ID,
        "resumeAnalysisId": ANALYSIS_ID,
        "tailoringId": TAILORING_ID,
        "interviewPrepId": INTERVIEW_PREP_ID,
        "status": "processing",
        "version": 2,
        "jobName": "Director of Software Engineering",
        "jobUrl": "https://example.com/jobs/123",
        "createdAt": "2026-07-15T00:00:00+00:00",
    }

    dependencies.reserve_request.return_value = (
        IdempotencyReservation(
            disposition=DISPOSITION_REPLAY_COMPLETED,
            resource_id=MATCH_ID,
            status_code=202,
            response_body=stored_body,
        )
    )

    response = job_matching.match_job_description(make_event())

    assert response["statusCode"] == 202
    assert response_body(response) == stored_body

    dependencies.put_item_if_absent.assert_not_called()
    dependencies.put_items_and_outbox_if_absent.assert_not_called()
    dependencies.table.update_item.assert_not_called()
    dependencies.complete_request.assert_not_called()


def test_in_progress_replay_returns_same_match_without_work(
    dependencies,
):
    dependencies.reserve_request.return_value = (
        IdempotencyReservation(
            disposition=DISPOSITION_REPLAY_IN_PROGRESS,
            resource_id=MATCH_ID,
            status_code=202,
            response_body=None,
        )
    )

    response = job_matching.match_job_description(make_event())

    assert response["statusCode"] == 202
    assert response_body(response) == {
        "matchId": MATCH_ID,
        "status": "processing",
    }

    dependencies.put_item_if_absent.assert_not_called()
    dependencies.put_items_and_outbox_if_absent.assert_not_called()
    dependencies.table.update_item.assert_not_called()
    dependencies.complete_request.assert_not_called()


def test_existing_processing_match_does_not_redispatch(
    dependencies,
):
    existing_match = {
        "pk": f"USER#{USER_ID}",
        "sk": f"MATCH#{MATCH_ID}",
        "recordType": "jobMatch",
        "userId": USER_ID,
        "analysisId": MATCH_ID,
        "matchId": MATCH_ID,
        "resumeAnalysisId": ANALYSIS_ID,
        "tailoringId": TAILORING_ID,
        "interviewPrepId": INTERVIEW_PREP_ID,
        "createdAt": "2026-07-15T00:00:00+00:00",
        "createdByRequestHash": REQUEST_HASH,
        "status": "processing",
        "version": 2,
        "jobName": "Director of Software Engineering",
        "jobUrl": "https://example.com/jobs/123",
    }

    original_get_item = dependencies.table.get_item.side_effect

    def get_item(*, Key, ConsistentRead):
        if Key["sk"] == f"MATCH#{MATCH_ID}":
            return {"Item": existing_match}

        return original_get_item(
            Key=Key,
            ConsistentRead=ConsistentRead,
        )

    dependencies.table.get_item.side_effect = get_item

    response = job_matching.match_job_description(make_event())
    body = response_body(response)

    assert response["statusCode"] == 202
    assert body["status"] == "processing"
    assert body["version"] == 2

    dependencies.put_items_and_outbox_if_absent.assert_not_called()
    dependencies.table.update_item.assert_not_called()
    dependencies.complete_request.assert_called_once()


def test_outbox_transaction_failure_marks_request_retryable(
    dependencies,
):
    dependencies.put_items_and_outbox_if_absent.side_effect = (
        RuntimeError("DynamoDB transaction unavailable")
    )

    with pytest.raises(
        RuntimeError,
        match="DynamoDB transaction unavailable",
    ):
        job_matching.match_job_description(make_event())

    dependencies.mark_request_retryable.assert_called_once()
    dependencies.complete_request.assert_not_called()
    dependencies.table.update_item.assert_not_called()


def test_different_existing_match_request_is_rejected(
    dependencies,
):
    existing_match = {
        "pk": f"USER#{USER_ID}",
        "sk": f"MATCH#{MATCH_ID}",
        "recordType": "jobMatch",
        "userId": USER_ID,
        "matchId": MATCH_ID,
        "createdByRequestHash": "different-request-hash",
        "status": "QUEUED_PENDING_DISPATCH",
        "version": 1,
    }

    original_get_item = dependencies.table.get_item.side_effect

    def get_item(*, Key, ConsistentRead):
        if Key["sk"] == f"MATCH#{MATCH_ID}":
            return {"Item": existing_match}

        return original_get_item(
            Key=Key,
            ConsistentRead=ConsistentRead,
        )

    dependencies.table.get_item.side_effect = get_item

    with pytest.raises(
        RuntimeError,
        match="Job match identifier already exists",
    ):
        job_matching.match_job_description(make_event())

    dependencies.complete_request.assert_not_called()
    dependencies.mark_request_retryable.assert_called_once()
