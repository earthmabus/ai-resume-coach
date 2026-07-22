from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

import worker


KEY = {"pk": "USER#user-123", "sk": "RESUME#analysis-123"}
IDENTITY = {
    "jobType": "resumeAnalysis",
    "recordType": "resumeAnalysis",
    "recordId": "analysis-123",
    "key": KEY,
}


def item(status: str, *, version: int = 7, **extra) -> dict:
    return {
        "pk": KEY["pk"],
        "sk": KEY["sk"],
        "recordType": "resumeAnalysis",
        "analysisId": "analysis-123",
        "status": status,
        "version": version,
        **extra,
    }


def conditional_failure() -> ClientError:
    return ClientError(
        {
            "Error": {
                "Code": "ConditionalCheckFailedException",
                "Message": "condition failed",
            }
        },
        "UpdateItem",
    )


def configure_deterministic_claim(monkeypatch, table: MagicMock) -> None:
    monkeypatch.setattr(worker, "table", table)
    monkeypatch.setattr(worker.uuid, "uuid4", lambda: "attempt-123")
    monkeypatch.setattr(worker, "utc_now", lambda: "2026-07-21T02:30:00Z")
    monkeypatch.setattr(worker, "epoch_seconds", lambda: 1_000)
    monkeypatch.setattr(worker, "DEFAULT_LEASE_SECONDS", 300)


@pytest.mark.parametrize(
    "status",
    [
        worker.STATUS_PROCESSING,
        worker.STATUS_QUEUED_PENDING_DISPATCH,
        worker.STATUS_QUEUED,
        worker.STATUS_FAILED_RETRYABLE,
    ],
)
def test_resume_analysis_claimable_statuses_include_all_authorized_sources(status):
    assert status in worker.claimable_statuses("resumeAnalysis")


def test_resume_analysis_claimable_statuses_exclude_unrelated_states():
    statuses = worker.claimable_statuses("resumeAnalysis")

    assert worker.STATUS_WAITING not in statuses
    assert worker.STATUS_RESULT_READY not in statuses
    assert worker.STATUS_COMPLETED not in statuses
    assert worker.STATUS_FAILED_PERMANENT not in statuses
    assert worker.STATUS_FAILED_RETRY_EXHAUSTED not in statuses


@pytest.mark.parametrize("job_type", ["resumeTailoring", "interviewPreparation"])
def test_waiting_is_claimable_only_for_waiting_workflows(job_type):
    assert worker.STATUS_WAITING in worker.claimable_statuses(job_type)


def test_result_ready_is_claimable_only_for_job_match():
    assert worker.STATUS_RESULT_READY in worker.claimable_statuses("jobMatch")
    assert worker.STATUS_RESULT_READY not in worker.claimable_statuses("resumeAnalysis")


@pytest.mark.parametrize(
    "prior_status",
    [
        worker.STATUS_PROCESSING,
        worker.STATUS_QUEUED_PENDING_DISPATCH,
        worker.STATUS_QUEUED,
        worker.STATUS_FAILED_RETRYABLE,
    ],
)
def test_claim_job_claims_authorized_resume_analysis_state(
    monkeypatch,
    prior_status,
):
    original = item(prior_status)
    claimed = {
        **original,
        "status": worker.STATUS_WORKER_PROCESSING,
        "processingAttemptId": "attempt-123",
        "processingLeaseExpiresAt": 1_300,
        "version": 8,
    }
    table = MagicMock()
    table.get_item.return_value = {"Item": original}
    table.update_item.return_value = {"Attributes": claimed}
    configure_deterministic_claim(monkeypatch, table)

    result = worker.claim_job(IDENTITY)

    assert result == {
        "disposition": "CLAIMED",
        "item": claimed,
        "attemptId": "attempt-123",
        "priorStatus": prior_status,
    }

    update = table.update_item.call_args.kwargs
    assert update["Key"] == KEY
    assert update["ExpressionAttributeValues"][":expectedStatus"] == prior_status
    assert update["ExpressionAttributeValues"][":expectedVersion"] == 7
    assert (
        update["ExpressionAttributeValues"][":workerProcessing"]
        == worker.STATUS_WORKER_PROCESSING
    )
    assert update["ExpressionAttributeValues"][":leaseExpiresAt"] == 1_300
    assert update["ReturnValues"] == "ALL_NEW"


def test_queued_claim_uses_conditional_status_and_version_guard(monkeypatch):
    original = item(worker.STATUS_QUEUED, version=0)
    table = MagicMock()
    table.get_item.return_value = {"Item": original}
    table.update_item.return_value = {
        "Attributes": {
            **original,
            "status": worker.STATUS_WORKER_PROCESSING,
            "version": 1,
        }
    }
    configure_deterministic_claim(monkeypatch, table)

    worker.claim_job(IDENTITY)

    update = table.update_item.call_args.kwargs
    assert "#status = :expectedStatus" in update["ConditionExpression"]
    assert "#version = :expectedVersion" in update["ConditionExpression"]
    assert "attribute_not_exists(#version)" in update["ConditionExpression"]
    assert update["ExpressionAttributeNames"] == {
        "#status": "status",
        "#version": "version",
    }


def test_claim_job_uses_strongly_consistent_read(monkeypatch):
    table = MagicMock()
    table.get_item.return_value = {"Item": item(worker.STATUS_COMPLETED)}
    monkeypatch.setattr(worker, "table", table)

    worker.claim_job(IDENTITY)

    table.get_item.assert_called_once_with(Key=KEY, ConsistentRead=True)


def test_completed_delivery_is_idempotently_skipped(monkeypatch):
    completed = item(worker.STATUS_COMPLETED)
    table = MagicMock()
    table.get_item.return_value = {"Item": completed}
    monkeypatch.setattr(worker, "table", table)

    result = worker.claim_job(IDENTITY)

    assert result["disposition"] == "SKIP"
    assert result["priorStatus"] == worker.STATUS_COMPLETED
    table.update_item.assert_not_called()


@pytest.mark.parametrize(
    "status",
    [worker.STATUS_FAILED_PERMANENT, worker.STATUS_FAILED_RETRY_EXHAUSTED],
)
def test_unpublished_terminal_failure_is_not_silently_skipped(monkeypatch, status):
    terminal = item(status, terminalFailurePublished=False)
    table = MagicMock()
    table.get_item.return_value = {"Item": terminal}
    monkeypatch.setattr(worker, "table", table)

    result = worker.claim_job(IDENTITY)

    assert result["disposition"] == "TERMINAL_FAILURE_PENDING"
    assert result["priorStatus"] == status
    table.update_item.assert_not_called()


@pytest.mark.parametrize(
    "status",
    [worker.STATUS_FAILED_PERMANENT, worker.STATUS_FAILED_RETRY_EXHAUSTED],
)
def test_published_terminal_failure_is_idempotently_skipped(monkeypatch, status):
    terminal = item(status, terminalFailurePublished=True)
    table = MagicMock()
    table.get_item.return_value = {"Item": terminal}
    monkeypatch.setattr(worker, "table", table)

    result = worker.claim_job(IDENTITY)

    assert result["disposition"] == "SKIP"
    table.update_item.assert_not_called()


def test_active_worker_lease_is_skipped(monkeypatch):
    active = item(
        worker.STATUS_WORKER_PROCESSING,
        processingLeaseExpiresAt=1_001,
    )
    table = MagicMock()
    table.get_item.return_value = {"Item": active}
    monkeypatch.setattr(worker, "table", table)
    monkeypatch.setattr(worker, "epoch_seconds", lambda: 1_000)

    result = worker.claim_job(IDENTITY)

    assert result["disposition"] == "SKIP"
    assert result["priorStatus"] == worker.STATUS_WORKER_PROCESSING
    table.update_item.assert_not_called()


def test_expired_worker_lease_can_be_reclaimed(monkeypatch):
    stale = item(
        worker.STATUS_WORKER_PROCESSING,
        processingLeaseExpiresAt=999,
    )
    reclaimed = {
        **stale,
        "processingAttemptId": "attempt-123",
        "processingLeaseExpiresAt": 1_300,
        "version": 8,
    }
    table = MagicMock()
    table.get_item.return_value = {"Item": stale}
    table.update_item.return_value = {"Attributes": reclaimed}
    configure_deterministic_claim(monkeypatch, table)

    result = worker.claim_job(IDENTITY)

    assert result["disposition"] == "CLAIMED"
    assert result["priorStatus"] == worker.STATUS_WORKER_PROCESSING
    assert result["attemptId"] == "attempt-123"


@pytest.mark.parametrize(
    "invalid_status",
    ["MYSTERY", "cancelled", "FAILED", "", None],
)
def test_unknown_or_unauthorized_status_is_rejected(monkeypatch, invalid_status):
    table = MagicMock()
    table.get_item.return_value = {"Item": item(invalid_status)}
    monkeypatch.setattr(worker, "table", table)

    with pytest.raises(RuntimeError, match="is not claimable"):
        worker.claim_job(IDENTITY)

    table.update_item.assert_not_called()


def test_missing_record_is_rejected(monkeypatch):
    table = MagicMock()
    table.get_item.return_value = {}
    monkeypatch.setattr(worker, "table", table)

    with pytest.raises(ValueError, match="resumeAnalysis not found"):
        worker.claim_job(IDENTITY)

    table.update_item.assert_not_called()


def test_claim_race_with_completed_record_is_skipped(monkeypatch):
    original = item(worker.STATUS_QUEUED)
    raced = item(worker.STATUS_COMPLETED, version=8)
    table = MagicMock()
    table.get_item.side_effect = [{"Item": original}, {"Item": raced}]
    table.update_item.side_effect = conditional_failure()
    configure_deterministic_claim(monkeypatch, table)

    result = worker.claim_job(IDENTITY)

    assert result["disposition"] == "SKIP"
    assert result["priorStatus"] == worker.STATUS_COMPLETED


def test_claim_race_with_other_worker_is_skipped(monkeypatch):
    original = item(worker.STATUS_QUEUED)
    raced = item(
        worker.STATUS_WORKER_PROCESSING,
        version=8,
        processingLeaseExpiresAt=1_300,
    )
    table = MagicMock()
    table.get_item.side_effect = [{"Item": original}, {"Item": raced}]
    table.update_item.side_effect = conditional_failure()
    configure_deterministic_claim(monkeypatch, table)

    result = worker.claim_job(IDENTITY)

    assert result["disposition"] == "SKIP"
    assert result["priorStatus"] == worker.STATUS_WORKER_PROCESSING


def test_claim_race_to_unexpected_state_propagates_failure(monkeypatch):
    original = item(worker.STATUS_QUEUED)
    raced = item(worker.STATUS_FAILED_RETRYABLE, version=8)
    error = conditional_failure()
    table = MagicMock()
    table.get_item.side_effect = [{"Item": original}, {"Item": raced}]
    table.update_item.side_effect = error
    configure_deterministic_claim(monkeypatch, table)

    with pytest.raises(ClientError) as captured:
        worker.claim_job(IDENTITY)

    assert captured.value is error


def test_nonconditional_storage_error_propagates(monkeypatch):
    original = item(worker.STATUS_QUEUED)
    error = ClientError(
        {"Error": {"Code": "ProvisionedThroughputExceededException"}},
        "UpdateItem",
    )
    table = MagicMock()
    table.get_item.return_value = {"Item": original}
    table.update_item.side_effect = error
    configure_deterministic_claim(monkeypatch, table)

    with pytest.raises(ClientError) as captured:
        worker.claim_job(IDENTITY)

    assert captured.value is error
