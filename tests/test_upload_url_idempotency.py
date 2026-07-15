from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from core.errors import IdempotencyKeyRequiredError
from core.idempotency import (
    DISPOSITION_REPLAY_COMPLETED,
    DISPOSITION_RESERVED,
    IdempotencyReservation,
)
from features import resume_analysis


USER_ID = "user-123"
REQUEST_ID = "request-123"
UPLOAD_ID = "upload-123"
IDEMPOTENCY_KEY = (
    "12345678-1234-1234-1234-123456789012"
)


def make_event(idempotency_key=IDEMPOTENCY_KEY):
    headers = {"Content-Type": "application/json"}

    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key

    return {
        "routeKey": "POST /resume-upload-url",
        "headers": headers,
        "body": json.dumps(
            {
                "fileName": "resume.pdf",
                "contentType": "application/pdf",
            }
        ),
        "requestContext": {
            "requestId": REQUEST_ID,
            "routeKey": "POST /resume-upload-url",
            "http": {
                "method": "POST",
                "path": "/resume-upload-url",
            },
            "authorizer": {
                "jwt": {
                    "claims": {"sub": USER_ID}
                }
            },
        },
    }


def response_body(response):
    return json.loads(response["body"])


def test_upload_url_requires_key(monkeypatch):
    with pytest.raises(IdempotencyKeyRequiredError):
        resume_analysis.create_resume_upload_url(
            make_event(idempotency_key=None)
        )


def test_first_request_uses_stable_upload_id(monkeypatch):
    reserve = MagicMock(
        return_value=IdempotencyReservation(
            disposition=DISPOSITION_RESERVED,
            resource_id=UPLOAD_ID,
        )
    )
    s3 = MagicMock()
    s3.generate_presigned_url.return_value = (
        "https://example.com/upload"
    )
    complete = MagicMock()

    monkeypatch.setattr(
        resume_analysis,
        "reserve_request",
        reserve,
    )
    monkeypatch.setattr(
        resume_analysis,
        "request_fingerprint",
        MagicMock(return_value="hash"),
    )
    monkeypatch.setattr(resume_analysis, "s3", s3)
    monkeypatch.setattr(
        resume_analysis,
        "complete_request",
        complete,
    )

    response = resume_analysis.create_resume_upload_url(
        make_event()
    )
    body = response_body(response)

    assert body["uploadId"] == UPLOAD_ID
    assert body["documentKey"] == (
        f"uploads/{USER_ID}/{UPLOAD_ID}/resume.pdf"
    )
    complete.assert_called_once()


def test_completed_replay_generates_fresh_url(monkeypatch):
    reserve = MagicMock(
        return_value=IdempotencyReservation(
            disposition=DISPOSITION_REPLAY_COMPLETED,
            resource_id=UPLOAD_ID,
            status_code=200,
            response_body={},
        )
    )
    s3 = MagicMock()
    s3.generate_presigned_url.return_value = (
        "https://example.com/fresh-upload"
    )
    complete = MagicMock()

    monkeypatch.setattr(
        resume_analysis,
        "reserve_request",
        reserve,
    )
    monkeypatch.setattr(
        resume_analysis,
        "request_fingerprint",
        MagicMock(return_value="hash"),
    )
    monkeypatch.setattr(resume_analysis, "s3", s3)
    monkeypatch.setattr(
        resume_analysis,
        "complete_request",
        complete,
    )

    response = resume_analysis.create_resume_upload_url(
        make_event()
    )

    assert response_body(response)["uploadUrl"] == (
        "https://example.com/fresh-upload"
    )
    s3.generate_presigned_url.assert_called_once()
    complete.assert_not_called()
