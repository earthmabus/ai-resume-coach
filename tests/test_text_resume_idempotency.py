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


USER_ID = "user-123"
REQUEST_ID = "request-123"
CORRELATION_ID = "correlation-123"
REQUEST_HASH = "request-hash-123"
ANALYSIS_ID = "analysis-123"
IDEMPOTENCY_KEY = (
    "12345678-1234-1234-1234-123456789012"
)


def make_event(
    *,
    idempotency_key=IDEMPOTENCY_KEY,
    body=None,
):
    headers = {
        "Content-Type": "application/json",
        "X-Correlation-Id": CORRELATION_ID,
    }

    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key

    return {
        "routeKey": "POST /analyze-resume",
        "headers": headers,
        "body": json.dumps(
            body
            or {
                "resumeName": "Engineering Resume",
                "resumeText": "Engineering leader",
                "analysisProvider": "rule-based",
            }
        ),
        "requestContext": {
            "requestId": REQUEST_ID,
            "routeKey": "POST /analyze-resume",
            "http": {
                "method": "POST",
                "path": "/analyze-resume",
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


@pytest.fixture
def dependencies(monkeypatch):
    reserve = MagicMock(
        return_value=IdempotencyReservation(
            disposition=DISPOSITION_RESERVED,
            resource_id=ANALYSIS_ID,
        )
    )
    analyze_and_save = MagicMock(
        return_value={
            "analysisId": ANALYSIS_ID,
            "status": "completed",
            "version": 2,
            "sourceType": "text",
            "resumeName": "Engineering Resume",
            "createdAt": "2026-07-15T00:00:00+00:00",
            "provider": "rule-based",
            "model": "",
            "analysisVersion": "test-v1",
            "analysisDurationMs": 10,
            "score": 90,
            "wordCount": 2,
            "strengths": ["Leadership"],
            "recommendations": ["Add metrics"],
            "executiveSummary": "Summary",
            "targetRoleTitle": "Director",
            "targetIndustry": "Technology",
            "dynamicScores": [],
            "roleFitSummary": "Strong fit",
            "roleSpecificGaps": [],
        }
    )
    complete = MagicMock()
    retryable = MagicMock()

    monkeypatch.setattr(
        resume_analysis,
        "reserve_request",
        reserve,
    )
    monkeypatch.setattr(
        resume_analysis,
        "request_fingerprint",
        MagicMock(return_value=REQUEST_HASH),
    )
    monkeypatch.setattr(
        resume_analysis,
        "analyze_and_save_resume",
        analyze_and_save,
    )
    monkeypatch.setattr(
        resume_analysis,
        "complete_request",
        complete,
    )
    monkeypatch.setattr(
        resume_analysis,
        "mark_request_retryable",
        retryable,
    )
    monkeypatch.setattr(
        resume_analysis,
        "get_target_career_for_user",
        MagicMock(
            return_value={
                "roleTitle": "Director",
                "industry": "Technology",
            }
        ),
    )

    return SimpleNamespace(
        reserve=reserve,
        analyze_and_save=analyze_and_save,
        complete=complete,
        retryable=retryable,
    )


def test_missing_key_is_rejected(dependencies):
    with pytest.raises(IdempotencyKeyRequiredError):
        resume_analysis.analyze_resume(
            make_event(idempotency_key=None)
        )


def test_first_request_runs_analysis_once(dependencies):
    response = resume_analysis.analyze_resume(
        make_event()
    )

    assert response["statusCode"] == 200
    assert response_body(response)["analysisId"] == ANALYSIS_ID
    dependencies.analyze_and_save.assert_called_once()
    assert (
        dependencies.analyze_and_save
        .call_args.kwargs["correlation_id"]
        == CORRELATION_ID
    )
    dependencies.complete.assert_called_once()


def test_completed_replay_skips_model(dependencies):
    dependencies.reserve.return_value = (
        IdempotencyReservation(
            disposition=DISPOSITION_REPLAY_COMPLETED,
            resource_id=ANALYSIS_ID,
            status_code=200,
            response_body={
                "analysisId": ANALYSIS_ID,
                "status": "completed",
            },
        )
    )

    response = resume_analysis.analyze_resume(
        make_event()
    )

    assert response["statusCode"] == 200
    dependencies.analyze_and_save.assert_not_called()


def test_in_progress_replay_skips_model(dependencies):
    dependencies.reserve.return_value = (
        IdempotencyReservation(
            disposition=DISPOSITION_REPLAY_IN_PROGRESS,
            resource_id=ANALYSIS_ID,
            status_code=202,
        )
    )

    response = resume_analysis.analyze_resume(
        make_event()
    )

    assert response["statusCode"] == 202
    assert response_body(response)["analysisId"] == ANALYSIS_ID
    dependencies.analyze_and_save.assert_not_called()


def test_model_failure_marks_retryable(dependencies):
    dependencies.analyze_and_save.side_effect = RuntimeError(
        "Provider failed"
    )

    with pytest.raises(RuntimeError):
        resume_analysis.analyze_resume(make_event())

    dependencies.retryable.assert_called_once()
    dependencies.complete.assert_not_called()
