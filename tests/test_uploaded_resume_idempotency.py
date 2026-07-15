from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

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

    return {
        "routeKey": "POST /analyze-uploaded-resume",
        "headers": headers,
        "body": json.dumps(
            body
            or {
                "documentBucket": "test-bucket",
                "documentKey": (
                    "users/user-123/resumes/resume.pdf"
                ),
                "fileName": "resume.pdf",
                "resumeName": "Engineering Resume",
                "analysisProvider": "openai",
            }
        ),
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


@pytest.fixture
def target_career():
    return {
        "roleTitle": "Director of Software Engineering",
        "industry": "Technology",
    }


def response_body(response: dict) -> dict:
    return json.loads(response["body"])


def test_missing_idempotency_key_is_rejected():
    event = make_event(idempotency_key=None)

    with patch.object(
        resume_analysis,
        "get_target_career_for_user",
        return_value={
            "roleTitle": "Director",
            "industry": "Technology",
        },
    ):
        with pytest.raises(IdempotencyKeyRequiredError):
            resume_analysis.analyze_uploaded_resume(event)


@patch.object(resume_analysis, "complete_request")
@patch.object(resume_analysis, "sqs")
@patch.object(resume_analysis, "table")
@patch.object(resume_analysis, "put_item_if_absent")
@patch.object(resume_analysis, "extract_text_from_pdf")
@patch.object(resume_analysis, "reserve_request")
@patch.object(
    resume_analysis,
    "get_target_career_for_user",
)
def test_first_submission_creates_one_item_and_sends_one_message(
    mock_get_target_career,
    mock_reserve_request,
    mock_extract_text,
    mock_put_item_if_absent,
    mock_table,
    mock_sqs,
    mock_complete_request,
    target_career,
):
    mock_get_target_career.return_value = target_career
    mock_reserve_request.return_value = IdempotencyReservation(
        disposition=DISPOSITION_RESERVED,
        resource_id=ANALYSIS_ID,
    )
    mock_extract_text.return_value = (
        "Experienced engineering leader with cloud expertise."
    )
    mock_put_item_if_absent.return_value = True
    mock_table.update_item.return_value = {}

    response = resume_analysis.analyze_uploaded_resume(
        make_event()
    )

    body = response_body(response)

    assert response["statusCode"] == 202
    assert body["analysisId"] == ANALYSIS_ID
    assert body["status"] == "processing"

    mock_put_item_if_absent.assert_called_once()
    mock_sqs.send_message.assert_called_once()
    mock_table.update_item.assert_called_once()
    mock_complete_request.assert_called_once()

    created_item = mock_put_item_if_absent.call_args.args[0]

    assert created_item["analysisId"] == ANALYSIS_ID
    assert created_item["status"] == "QUEUED_PENDING_DISPATCH"
    assert created_item["version"] == 1
    assert created_item["createdByRequestId"] == REQUEST_ID
    assert created_item["createdRegion"] == "us-east-1"

    queue_message = json.loads(
        mock_sqs.send_message.call_args.kwargs["MessageBody"]
    )

    assert queue_message["schemaVersion"] == 1
    assert queue_message["analysisId"] == ANALYSIS_ID
    assert queue_message["jobId"] == ANALYSIS_ID
    assert queue_message["userId"] == USER_ID
    assert queue_message["requestId"] == REQUEST_ID
    assert queue_message["sourceRegion"] == "us-east-1"


@patch.object(resume_analysis, "complete_request")
@patch.object(resume_analysis, "sqs")
@patch.object(resume_analysis, "put_item_if_absent")
@patch.object(resume_analysis, "extract_text_from_pdf")
@patch.object(resume_analysis, "reserve_request")
@patch.object(
    resume_analysis,
    "get_target_career_for_user",
)
def test_completed_replay_does_not_repeat_work(
    mock_get_target_career,
    mock_reserve_request,
    mock_extract_text,
    mock_put_item_if_absent,
    mock_sqs,
    mock_complete_request,
    target_career,
):
    stored_body = {
        "analysisId": ANALYSIS_ID,
        "status": "processing",
        "version": 2,
    }

    mock_get_target_career.return_value = target_career
    mock_reserve_request.return_value = IdempotencyReservation(
        disposition=DISPOSITION_REPLAY_COMPLETED,
        resource_id=ANALYSIS_ID,
        status_code=202,
        response_body=stored_body,
    )

    response = resume_analysis.analyze_uploaded_resume(
        make_event()
    )

    assert response["statusCode"] == 202
    assert response_body(response) == stored_body

    mock_extract_text.assert_not_called()
    mock_put_item_if_absent.assert_not_called()
    mock_sqs.send_message.assert_not_called()
    mock_complete_request.assert_not_called()


@patch.object(resume_analysis, "complete_request")
@patch.object(resume_analysis, "sqs")
@patch.object(resume_analysis, "put_item_if_absent")
@patch.object(resume_analysis, "extract_text_from_pdf")
@patch.object(resume_analysis, "reserve_request")
@patch.object(
    resume_analysis,
    "get_target_career_for_user",
)
def test_in_progress_replay_returns_same_analysis_without_work(
    mock_get_target_career,
    mock_reserve_request,
    mock_extract_text,
    mock_put_item_if_absent,
    mock_sqs,
    mock_complete_request,
    target_career,
):
    mock_get_target_career.return_value = target_career
    mock_reserve_request.return_value = IdempotencyReservation(
        disposition=DISPOSITION_REPLAY_IN_PROGRESS,
        resource_id=ANALYSIS_ID,
        status_code=202,
        response_body=None,
    )

    response = resume_analysis.analyze_uploaded_resume(
        make_event()
    )

    body = response_body(response)

    assert response["statusCode"] == 202
    assert body == {
        "analysisId": ANALYSIS_ID,
        "status": "processing",
    }

    mock_extract_text.assert_not_called()
    mock_put_item_if_absent.assert_not_called()
    mock_sqs.send_message.assert_not_called()
    mock_complete_request.assert_not_called()


@patch.object(resume_analysis, "complete_request")
@patch.object(resume_analysis, "mark_request_retryable")
@patch.object(resume_analysis, "sqs")
@patch.object(resume_analysis, "table")
@patch.object(resume_analysis, "put_item_if_absent")
@patch.object(resume_analysis, "extract_text_from_pdf")
@patch.object(resume_analysis, "reserve_request")
@patch.object(
    resume_analysis,
    "get_target_career_for_user",
)
def test_sqs_failure_marks_request_retryable(
    mock_get_target_career,
    mock_reserve_request,
    mock_extract_text,
    mock_put_item_if_absent,
    mock_table,
    mock_sqs,
    mock_mark_request_retryable,
    mock_complete_request,
    target_career,
):
    mock_get_target_career.return_value = target_career
    mock_reserve_request.return_value = IdempotencyReservation(
        disposition=DISPOSITION_RESERVED,
        resource_id=ANALYSIS_ID,
    )
    mock_extract_text.return_value = "Resume text"
    mock_put_item_if_absent.return_value = True
    mock_sqs.send_message.side_effect = RuntimeError(
        "SQS unavailable"
    )

    with pytest.raises(RuntimeError, match="SQS unavailable"):
        resume_analysis.analyze_uploaded_resume(
            make_event()
        )

    mock_mark_request_retryable.assert_called_once()
    mock_complete_request.assert_not_called()
    mock_table.update_item.assert_not_called()


@patch.object(resume_analysis, "complete_request")
@patch.object(resume_analysis, "sqs")
@patch.object(resume_analysis, "put_item_if_absent")
@patch.object(resume_analysis, "extract_text_from_pdf")
@patch.object(resume_analysis, "reserve_request")
@patch.object(
    resume_analysis,
    "get_target_career_for_user",
)
def test_empty_pdf_text_completes_deterministic_400_response(
    mock_get_target_career,
    mock_reserve_request,
    mock_extract_text,
    mock_put_item_if_absent,
    mock_sqs,
    mock_complete_request,
    target_career,
):
    mock_get_target_career.return_value = target_career
    mock_reserve_request.return_value = IdempotencyReservation(
        disposition=DISPOSITION_RESERVED,
        resource_id=ANALYSIS_ID,
    )
    mock_extract_text.return_value = ""

    response = resume_analysis.analyze_uploaded_resume(
        make_event()
    )

    body = response_body(response)

    assert response["statusCode"] == 400
    assert body["analysisId"] == ANALYSIS_ID
    assert "No resume text" in body["error"]

    mock_complete_request.assert_called_once()

    completion = mock_complete_request.call_args.kwargs

    assert completion["status_code"] == 400
    assert completion["resource_id"] == ANALYSIS_ID

    mock_put_item_if_absent.assert_not_called()
    mock_sqs.send_message.assert_not_called()


@patch.object(resume_analysis, "complete_request")
@patch.object(resume_analysis, "sqs")
@patch.object(resume_analysis, "table")
@patch.object(resume_analysis, "put_item_if_absent")
@patch.object(resume_analysis, "extract_text_from_pdf")
@patch.object(resume_analysis, "reserve_request")
@patch.object(
    resume_analysis,
    "get_target_career_for_user",
)
def test_existing_item_from_same_request_can_continue(
    mock_get_target_career,
    mock_reserve_request,
    mock_extract_text,
    mock_put_item_if_absent,
    mock_table,
    mock_sqs,
    mock_complete_request,
    target_career,
):
    mock_get_target_career.return_value = target_career
    mock_reserve_request.return_value = IdempotencyReservation(
        disposition=DISPOSITION_RESERVED,
        resource_id=ANALYSIS_ID,
    )
    mock_extract_text.return_value = "Resume text"
    mock_put_item_if_absent.return_value = False

    existing_item = {
        "pk": f"USER#{USER_ID}",
        "sk": f"RESUME#{ANALYSIS_ID}",
        "analysisId": ANALYSIS_ID,
        "createdByRequestId": REQUEST_ID,
        "status": "QUEUED_PENDING_DISPATCH",
        "version": 1,
    }

    mock_table.get_item.return_value = {
        "Item": existing_item,
    }

    response = resume_analysis.analyze_uploaded_resume(
        make_event()
    )

    assert response["statusCode"] == 202
    mock_table.get_item.assert_called_once()
    mock_sqs.send_message.assert_called_once()
    mock_complete_request.assert_called_once()


@patch.object(resume_analysis, "complete_request")
@patch.object(resume_analysis, "mark_request_retryable")
@patch.object(resume_analysis, "sqs")
@patch.object(resume_analysis, "table")
@patch.object(resume_analysis, "put_item_if_absent")
@patch.object(resume_analysis, "extract_text_from_pdf")
@patch.object(resume_analysis, "reserve_request")
@patch.object(
    resume_analysis,
    "get_target_career_for_user",
)
def test_existing_item_from_different_request_is_rejected(
    mock_get_target_career,
    mock_reserve_request,
    mock_extract_text,
    mock_put_item_if_absent,
    mock_table,
    mock_sqs,
    mock_mark_request_retryable,
    mock_complete_request,
    target_career,
):
    mock_get_target_career.return_value = target_career
    mock_reserve_request.return_value = IdempotencyReservation(
        disposition=DISPOSITION_RESERVED,
        resource_id=ANALYSIS_ID,
    )
    mock_extract_text.return_value = "Resume text"
    mock_put_item_if_absent.return_value = False

    mock_table.get_item.return_value = {
        "Item": {
            "analysisId": ANALYSIS_ID,
            "createdByRequestId": "different-request",
        }
    }

    with pytest.raises(
        RuntimeError,
        match="Analysis identifier already exists",
    ):
        resume_analysis.analyze_uploaded_resume(
            make_event()
        )

    mock_sqs.send_message.assert_not_called()
    mock_complete_request.assert_not_called()
    mock_mark_request_retryable.assert_called_once()
