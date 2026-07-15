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
from features import resume_tailoring


IDEMPOTENCY_KEY = "12345678-1234-1234-1234-123456789012"
USER_ID = "user-123"
REQUEST_ID = "request-123"
REQUEST_HASH = "request-hash-123"
MATCH_ID = "11111111-1111-4111-8111-111111111111"
TAILORING_ID = "22222222-2222-4222-8222-222222222222"


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
        "routeKey": "POST /tailor-resume",
        "headers": headers,
        "body": json.dumps(
            body
            or {
                "matchId": MATCH_ID,
                "analysisProvider": "rule-based",
            }
        ),
        "requestContext": {
            "requestId": REQUEST_ID,
            "routeKey": "POST /tailor-resume",
            "http": {
                "method": "POST",
                "path": "/tailor-resume",
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
    match_item = {
        "pk": f"USER#{USER_ID}",
        "sk": f"MATCH#{MATCH_ID}",
        "recordType": "jobMatch",
        "userId": USER_ID,
        "matchId": MATCH_ID,
        "tailoringId": TAILORING_ID,
        "provider": "rule-based",
        "status": "completed",
        "version": 3,
    }

    tailoring_item = {
        "pk": f"MATCH#{MATCH_ID}",
        "sk": f"TAILORING#{TAILORING_ID}",
        "recordType": "resumeTailoring",
        "userId": USER_ID,
        "matchId": MATCH_ID,
        "tailoringId": TAILORING_ID,
        "createdAt": "2026-07-15T00:00:00+00:00",
        "status": "waiting",
        "version": 1,
    }

    table = MagicMock()

    def get_item(*, Key, ConsistentRead):
        if Key["sk"] == f"MATCH#{MATCH_ID}":
            return {"Item": match_item}

        if Key["sk"] == f"TAILORING#{TAILORING_ID}":
            return {"Item": tailoring_item}

        return {}

    table.get_item.side_effect = get_item

    table.update_item.return_value = {
        "Attributes": {
            **tailoring_item,
            "status": "processing",
            "version": 2,
        }
    }

    sqs = MagicMock()

    reserve_request = MagicMock(
        return_value=IdempotencyReservation(
            disposition=DISPOSITION_RESERVED,
            resource_id=TAILORING_ID,
        )
    )

    complete_request = MagicMock()
    mark_request_retryable = MagicMock()
    request_fingerprint = MagicMock(return_value=REQUEST_HASH)

    monkeypatch.setattr(resume_tailoring, "table", table)
    monkeypatch.setattr(resume_tailoring, "sqs", sqs)
    monkeypatch.setattr(
        resume_tailoring,
        "reserve_request",
        reserve_request,
    )
    monkeypatch.setattr(
        resume_tailoring,
        "complete_request",
        complete_request,
    )
    monkeypatch.setattr(
        resume_tailoring,
        "mark_request_retryable",
        mark_request_retryable,
    )
    monkeypatch.setattr(
        resume_tailoring,
        "request_fingerprint",
        request_fingerprint,
    )

    return SimpleNamespace(
        match_item=match_item,
        tailoring_item=tailoring_item,
        table=table,
        sqs=sqs,
        reserve_request=reserve_request,
        complete_request=complete_request,
        mark_request_retryable=mark_request_retryable,
        request_fingerprint=request_fingerprint,
    )


def test_missing_idempotency_key_is_rejected(dependencies):
    with pytest.raises(IdempotencyKeyRequiredError):
        resume_tailoring.tailor_resume(
            make_event(idempotency_key=None)
        )

    dependencies.reserve_request.assert_not_called()
    dependencies.sqs.send_message.assert_not_called()


def test_missing_match_id_returns_400(dependencies):
    response = resume_tailoring.tailor_resume(
        make_event(body={"matchId": ""})
    )

    assert response["statusCode"] == 400
    assert response_body(response) == {
        "error": "matchId is required"
    }

    dependencies.reserve_request.assert_not_called()


def test_match_is_read_by_base_table_key(dependencies):
    response = resume_tailoring.tailor_resume(make_event())

    assert response["statusCode"] == 202

    dependencies.table.get_item.assert_any_call(
        Key={
            "pk": f"USER#{USER_ID}",
            "sk": f"MATCH#{MATCH_ID}",
        },
        ConsistentRead=True,
    )


def test_waiting_tailoring_is_dispatched(dependencies):
    response = resume_tailoring.tailor_resume(make_event())
    body = response_body(response)

    assert response["statusCode"] == 202
    assert body == {
        "tailoringId": TAILORING_ID,
        "matchId": MATCH_ID,
        "status": "processing",
        "version": 2,
        "createdAt": "2026-07-15T00:00:00+00:00",
    }

    dependencies.sqs.send_message.assert_called_once()
    dependencies.table.update_item.assert_called_once()
    dependencies.complete_request.assert_called_once()

    message = json.loads(
        dependencies.sqs.send_message.call_args.kwargs[
            "MessageBody"
        ]
    )

    assert message["jobType"] == "resumeTailoring"
    assert message["tailoringId"] == TAILORING_ID
    assert message["jobId"] == TAILORING_ID
    assert message["matchId"] == MATCH_ID
    assert message["requestHash"] == REQUEST_HASH
    assert message["sourceRegion"] == "us-east-1"


def test_existing_processing_tailoring_is_not_redispatched(
    dependencies,
):
    dependencies.tailoring_item["status"] = "processing"
    dependencies.tailoring_item["version"] = 2

    response = resume_tailoring.tailor_resume(make_event())
    body = response_body(response)

    assert response["statusCode"] == 202
    assert body["status"] == "processing"
    assert body["version"] == 2

    dependencies.sqs.send_message.assert_not_called()
    dependencies.table.update_item.assert_not_called()
    dependencies.complete_request.assert_called_once()


def test_existing_completed_tailoring_is_not_redispatched(
    dependencies,
):
    dependencies.tailoring_item["status"] = "completed"
    dependencies.tailoring_item["version"] = 3

    response = resume_tailoring.tailor_resume(make_event())
    body = response_body(response)

    assert response["statusCode"] == 202
    assert body["status"] == "completed"
    assert body["version"] == 3

    dependencies.sqs.send_message.assert_not_called()
    dependencies.table.update_item.assert_not_called()
    dependencies.complete_request.assert_called_once()


def test_completed_replay_does_not_read_or_dispatch(
    dependencies,
):
    stored_body = {
        "tailoringId": TAILORING_ID,
        "matchId": MATCH_ID,
        "status": "processing",
        "version": 2,
        "createdAt": "2026-07-15T00:00:00+00:00",
    }

    dependencies.reserve_request.return_value = (
        IdempotencyReservation(
            disposition=DISPOSITION_REPLAY_COMPLETED,
            resource_id=TAILORING_ID,
            status_code=202,
            response_body=stored_body,
        )
    )

    response = resume_tailoring.tailor_resume(make_event())

    assert response["statusCode"] == 202
    assert response_body(response) == stored_body

    assert dependencies.table.get_item.call_count == 1
    dependencies.sqs.send_message.assert_not_called()
    dependencies.table.update_item.assert_not_called()
    dependencies.complete_request.assert_not_called()


def test_in_progress_replay_returns_same_tailoring(
    dependencies,
):
    dependencies.reserve_request.return_value = (
        IdempotencyReservation(
            disposition=DISPOSITION_REPLAY_IN_PROGRESS,
            resource_id=TAILORING_ID,
            status_code=202,
            response_body=None,
        )
    )

    response = resume_tailoring.tailor_resume(make_event())

    assert response["statusCode"] == 202
    assert response_body(response) == {
        "tailoringId": TAILORING_ID,
        "matchId": MATCH_ID,
        "status": "processing",
    }

    dependencies.sqs.send_message.assert_not_called()
    dependencies.table.update_item.assert_not_called()
    dependencies.complete_request.assert_not_called()


def test_sqs_failure_marks_request_retryable(dependencies):
    dependencies.sqs.send_message.side_effect = RuntimeError(
        "SQS unavailable"
    )

    with pytest.raises(RuntimeError, match="SQS unavailable"):
        resume_tailoring.tailor_resume(make_event())

    dependencies.mark_request_retryable.assert_called_once()
    dependencies.complete_request.assert_not_called()
    dependencies.table.update_item.assert_not_called()


def test_missing_stable_tailoring_record_returns_404(
    dependencies,
):
    original_get_item = dependencies.table.get_item.side_effect

    def get_item(*, Key, ConsistentRead):
        if Key["sk"] == f"TAILORING#{TAILORING_ID}":
            return {}

        return original_get_item(
            Key=Key,
            ConsistentRead=ConsistentRead,
        )

    dependencies.table.get_item.side_effect = get_item

    response = resume_tailoring.tailor_resume(make_event())

    assert response["statusCode"] == 404
    assert response_body(response)["tailoringId"] == TAILORING_ID

    dependencies.complete_request.assert_called_once()
    dependencies.sqs.send_message.assert_not_called()
