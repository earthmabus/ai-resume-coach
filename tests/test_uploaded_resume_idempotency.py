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
from features import resume_analysis


IDEMPOTENCY_KEY = "12345678-1234-1234-1234-123456789012"
USER_ID = "user-123"
REQUEST_ID = "request-123"
ANALYSIS_ID = "analysis-123"
REQUEST_HASH = "request-hash-123"


def make_event(
    *,
    idempotency_key: str | None = IDEMPOTENCY_KEY,
    body: dict | None = None,
) -> dict:
    headers = {
        "Content-Type": "application/json",
    }

    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key

    payload = body or {
        "documentBucket": "test-bucket",
        "documentKey": "users/user-123/resumes/resume.pdf",
        "fileName": "resume.pdf",
        "resumeName": "Engineering Resume",
        "analysisProvider": "rule-based",
    }

    return {
        "routeKey": "POST /analyze-uploaded-resume",
        "headers": headers,
        "body": json.dumps(payload),
        "requestContext": {
            "requestId": REQUEST_ID,
            "routeKey": "POST /analyze-uploaded-resume",
            "http": {
                "method": "POST",
                "path": "/analyze-uploaded-resume",
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
def target_career():
    return {
        "roleTitle": "Director of Software Engineering",
        "industry": "Technology",
    }


@pytest.fixture
def dependencies(monkeypatch, target_career):
    table = MagicMock()
    table.get_item.return_value = {}
    table.update_item.return_value = {
        "Attributes": {
            "analysisId": ANALYSIS_ID,
            "status": "processing",
            "version": 2,
            "resumeName": "Engineering Resume",
            "createdAt": "2026-07-15T00:00:00+00:00",
            "sourceType": "pdf",
        }
    }

    sqs = MagicMock()
    reserve_request = MagicMock(
        return_value=IdempotencyReservation(
            disposition=DISPOSITION_RESERVED,
            resource_id=ANALYSIS_ID,
        )
    )
    extract_text = MagicMock(return_value="Resume text")
    put_item_if_absent = MagicMock(return_value=True)
    complete_request = MagicMock()
    mark_request_retryable = MagicMock()
    request_fingerprint = MagicMock(return_value=REQUEST_HASH)
    get_target_career = MagicMock(return_value=target_career)

    monkeypatch.setattr(resume_analysis, "table", table)
    monkeypatch.setattr(resume_analysis, "sqs", sqs)
    monkeypatch.setattr(
        resume_analysis,
        "reserve_request",
        reserve_request,
    )
    monkeypatch.setattr(
        resume_analysis,
        "extract_text_from_pdf",
        extract_text,
    )
    monkeypatch.setattr(
        resume_analysis,
        "put_item_if_absent",
        put_item_if_absent,
    )
    monkeypatch.setattr(
        resume_analysis,
        "complete_request",
        complete_request,
    )
    monkeypatch.setattr(
        resume_analysis,
        "mark_request_retryable",
        mark_request_retryable,
    )
    monkeypatch.setattr(
        resume_analysis,
        "request_fingerprint",
        request_fingerprint,
    )
    monkeypatch.setattr(
        resume_analysis,
        "get_target_career_for_user",
        get_target_career,
    )

    return SimpleNamespace(
        table=table,
        sqs=sqs,
        reserve_request=reserve_request,
        extract_text=extract_text,
        put_item_if_absent=put_item_if_absent,
        complete_request=complete_request,
        mark_request_retryable=mark_request_retryable,
        request_fingerprint=request_fingerprint,
        get_target_career=get_target_career,
    )


def test_missing_idempotency_key_is_rejected(dependencies):
    with pytest.raises(IdempotencyKeyRequiredError):
        resume_analysis.analyze_uploaded_resume(
            make_event(idempotency_key=None)
        )

    dependencies.reserve_request.assert_not_called()
    dependencies.table.get_item.assert_not_called()


def test_invalid_document_bucket_returns_400(dependencies):
    response = resume_analysis.analyze_uploaded_resume(
        make_event(
            body={
                "documentBucket": "unapproved-bucket",
                "documentKey": "uploads/example/resume.pdf",
                "fileName": "resume.pdf",
                "resumeName": "Engineering Resume",
                "analysisProvider": "rule-based",
            }
        )
    )

    assert response["statusCode"] == 400
    assert response_body(response) == {
        "error": "Invalid document bucket"
    }

    dependencies.request_fingerprint.assert_not_called()
    dependencies.reserve_request.assert_not_called()
    dependencies.table.get_item.assert_not_called()


def test_first_submission_creates_one_item_and_sends_one_message(
    dependencies,
):
    response = resume_analysis.analyze_uploaded_resume(make_event())
    body = response_body(response)

    assert response["statusCode"] == 202
    assert body["analysisId"] == ANALYSIS_ID
    assert body["status"] == "processing"
    assert body["version"] == 2
    assert "resumeText" not in body

    dependencies.table.get_item.assert_called_once_with(
        Key={
            "pk": f"USER#{USER_ID}",
            "sk": f"RESUME#{ANALYSIS_ID}",
        },
        ConsistentRead=True,
    )
    dependencies.extract_text.assert_called_once_with(
        "test-bucket",
        "users/user-123/resumes/resume.pdf",
    )
    dependencies.put_item_if_absent.assert_called_once()
    dependencies.sqs.send_message.assert_called_once()
    dependencies.table.update_item.assert_called_once()
    dependencies.complete_request.assert_called_once()

    created_item = dependencies.put_item_if_absent.call_args.args[0]

    assert created_item["analysisId"] == ANALYSIS_ID
    assert created_item["status"] == "QUEUED_PENDING_DISPATCH"
    assert created_item["version"] == 1
    assert created_item["createdByRequestHash"] == REQUEST_HASH
    assert created_item["createdByRequestId"] == REQUEST_ID
    assert created_item["createdRegion"] == "us-east-1"

    queue_message = json.loads(
        dependencies.sqs.send_message.call_args.kwargs[
            "MessageBody"
        ]
    )

    assert queue_message["schemaVersion"] == 1
    assert queue_message["jobId"] == ANALYSIS_ID
    assert queue_message["analysisId"] == ANALYSIS_ID
    assert queue_message["userId"] == USER_ID
    assert queue_message["requestId"] == REQUEST_ID
    assert queue_message["requestHash"] == REQUEST_HASH
    assert queue_message["sourceRegion"] == "us-east-1"

    completion = dependencies.complete_request.call_args.kwargs
    assert "resumeText" not in completion["response_body"]


def test_completed_replay_does_not_repeat_work(dependencies):
    stored_body = {
        "analysisId": ANALYSIS_ID,
        "status": "processing",
        "version": 2,
        "resumeName": "Engineering Resume",
        "createdAt": "2026-07-15T00:00:00+00:00",
        "sourceType": "pdf",
    }

    dependencies.reserve_request.return_value = (
        IdempotencyReservation(
            disposition=DISPOSITION_REPLAY_COMPLETED,
            resource_id=ANALYSIS_ID,
            status_code=202,
            response_body=stored_body,
        )
    )

    response = resume_analysis.analyze_uploaded_resume(make_event())

    assert response["statusCode"] == 202
    assert response_body(response) == stored_body

    dependencies.table.get_item.assert_not_called()
    dependencies.extract_text.assert_not_called()
    dependencies.put_item_if_absent.assert_not_called()
    dependencies.sqs.send_message.assert_not_called()
    dependencies.complete_request.assert_not_called()


def test_in_progress_replay_returns_same_analysis_without_work(
    dependencies,
):
    dependencies.reserve_request.return_value = (
        IdempotencyReservation(
            disposition=DISPOSITION_REPLAY_IN_PROGRESS,
            resource_id=ANALYSIS_ID,
            status_code=202,
            response_body=None,
        )
    )

    response = resume_analysis.analyze_uploaded_resume(make_event())

    assert response["statusCode"] == 202
    assert response_body(response) == {
        "analysisId": ANALYSIS_ID,
        "status": "processing",
    }

    dependencies.table.get_item.assert_not_called()
    dependencies.extract_text.assert_not_called()
    dependencies.put_item_if_absent.assert_not_called()
    dependencies.sqs.send_message.assert_not_called()
    dependencies.complete_request.assert_not_called()


def test_sqs_failure_marks_request_retryable(dependencies):
    dependencies.sqs.send_message.side_effect = RuntimeError(
        "SQS unavailable"
    )

    with pytest.raises(RuntimeError, match="SQS unavailable"):
        resume_analysis.analyze_uploaded_resume(make_event())

    dependencies.mark_request_retryable.assert_called_once()
    dependencies.complete_request.assert_not_called()
    dependencies.table.update_item.assert_not_called()


def test_empty_pdf_text_completes_deterministic_400_response(
    dependencies,
):
    dependencies.extract_text.return_value = ""

    response = resume_analysis.analyze_uploaded_resume(make_event())
    body = response_body(response)

    assert response["statusCode"] == 400
    assert body["analysisId"] == ANALYSIS_ID
    assert "No resume text" in body["error"]

    dependencies.complete_request.assert_called_once()

    completion = dependencies.complete_request.call_args.kwargs
    assert completion["status_code"] == 400
    assert completion["resource_id"] == ANALYSIS_ID

    dependencies.put_item_if_absent.assert_not_called()
    dependencies.sqs.send_message.assert_not_called()
    dependencies.table.update_item.assert_not_called()


def test_existing_pending_item_from_same_request_can_continue(
    dependencies,
):
    existing_item = {
        "pk": f"USER#{USER_ID}",
        "sk": f"RESUME#{ANALYSIS_ID}",
        "recordType": "resumeAnalysis",
        "userId": USER_ID,
        "analysisId": ANALYSIS_ID,
        "createdByRequestId": "original-gateway-request",
        "createdByRequestHash": REQUEST_HASH,
        "createdAt": "2026-07-15T00:00:00+00:00",
        "resumeName": "Engineering Resume",
        "sourceType": "pdf",
        "status": "QUEUED_PENDING_DISPATCH",
        "version": 1,
    }
    dependencies.table.get_item.return_value = {
        "Item": existing_item,
    }

    response = resume_analysis.analyze_uploaded_resume(make_event())

    assert response["statusCode"] == 202

    dependencies.extract_text.assert_not_called()
    dependencies.put_item_if_absent.assert_not_called()
    dependencies.sqs.send_message.assert_called_once()
    dependencies.table.update_item.assert_called_once()
    dependencies.complete_request.assert_called_once()


def test_existing_processing_item_does_not_repeat_dispatch(
    dependencies,
):
    existing_item = {
        "pk": f"USER#{USER_ID}",
        "sk": f"RESUME#{ANALYSIS_ID}",
        "recordType": "resumeAnalysis",
        "userId": USER_ID,
        "analysisId": ANALYSIS_ID,
        "createdByRequestHash": REQUEST_HASH,
        "createdAt": "2026-07-15T00:00:00+00:00",
        "resumeName": "Engineering Resume",
        "sourceType": "pdf",
        "status": "processing",
        "version": 2,
    }
    dependencies.table.get_item.return_value = {
        "Item": existing_item,
    }

    response = resume_analysis.analyze_uploaded_resume(make_event())
    body = response_body(response)

    assert response["statusCode"] == 202
    assert body["status"] == "processing"
    assert body["version"] == 2

    dependencies.extract_text.assert_not_called()
    dependencies.put_item_if_absent.assert_not_called()
    dependencies.sqs.send_message.assert_not_called()
    dependencies.table.update_item.assert_not_called()
    dependencies.complete_request.assert_called_once()


def test_existing_completed_item_does_not_repeat_dispatch(
    dependencies,
):
    existing_item = {
        "pk": f"USER#{USER_ID}",
        "sk": f"RESUME#{ANALYSIS_ID}",
        "recordType": "resumeAnalysis",
        "userId": USER_ID,
        "analysisId": ANALYSIS_ID,
        "createdByRequestHash": REQUEST_HASH,
        "createdAt": "2026-07-15T00:00:00+00:00",
        "resumeName": "Engineering Resume",
        "sourceType": "pdf",
        "status": "completed",
        "version": 3,
    }
    dependencies.table.get_item.return_value = {
        "Item": existing_item,
    }

    response = resume_analysis.analyze_uploaded_resume(make_event())
    body = response_body(response)

    assert response["statusCode"] == 202
    assert body["status"] == "completed"
    assert body["version"] == 3

    dependencies.extract_text.assert_not_called()
    dependencies.put_item_if_absent.assert_not_called()
    dependencies.sqs.send_message.assert_not_called()
    dependencies.table.update_item.assert_not_called()
    dependencies.complete_request.assert_called_once()


def test_existing_item_from_different_request_is_rejected(
    dependencies,
):
    dependencies.table.get_item.return_value = {
        "Item": {
            "pk": f"USER#{USER_ID}",
            "sk": f"RESUME#{ANALYSIS_ID}",
            "analysisId": ANALYSIS_ID,
            "createdByRequestHash": "different-request-hash",
            "status": "QUEUED_PENDING_DISPATCH",
            "version": 1,
        }
    }

    with pytest.raises(
        RuntimeError,
        match="Analysis identifier already exists",
    ):
        resume_analysis.analyze_uploaded_resume(make_event())

    dependencies.extract_text.assert_not_called()
    dependencies.put_item_if_absent.assert_not_called()
    dependencies.sqs.send_message.assert_not_called()
    dependencies.complete_request.assert_not_called()
    dependencies.mark_request_retryable.assert_called_once()
