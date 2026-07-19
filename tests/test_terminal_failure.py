from __future__ import annotations

import json

from core.terminal_failure import TerminalFailureEnvelope


def test_terminal_failure_envelope_is_deterministic_and_privacy_bounded():
    envelope = TerminalFailureEnvelope(
        failure_id="failure-1",
        work_id="analysis-1",
        job_type="resumeAnalysis",
        record_type="resumeAnalysis",
        status="FAILED_PERMANENT",
        failure_category="PERMANENT",
        processing_attempt=1,
        max_processing_attempts=5,
        error_type="ValueError",
        error_message="bad input",
        request_id="request-1",
        correlation_id="correlation-1",
        outbox_event_id="outbox-1",
        owner_region="us-east-1",
        source_region="us-west-2",
        failed_region="us-east-1",
        deployment_id="deploy-1",
        failed_at="2026-07-18T12:00:00+00:00",
    )

    payload = json.loads(envelope.to_json())

    assert payload["eventType"] == "WORKFLOW_TERMINAL_FAILURE"
    assert payload["failureId"] == "failure-1"
    assert payload["workId"] == "analysis-1"
    assert payload["failureCategory"] == "PERMANENT"
    assert "resumeText" not in payload
    assert "documentKey" not in payload


def test_terminal_failure_error_message_is_truncated():
    envelope = TerminalFailureEnvelope(
        failure_id="failure-1", work_id="work-1", job_type="jobMatch",
        record_type="jobMatch", status="FAILED_RETRY_EXHAUSTED",
        failure_category="PROVIDER_UNAVAILABLE", processing_attempt=5,
        max_processing_attempts=5, error_type="TimeoutError",
        error_message="x" * 2500, request_id="", correlation_id="",
        outbox_event_id="", owner_region="us-east-1",
        source_region="us-east-1", failed_region="us-east-1",
        deployment_id="deploy-1", failed_at="2026-07-18T12:00:00+00:00",
    )
    assert len(json.loads(envelope.to_json())["errorMessage"]) == 2000
