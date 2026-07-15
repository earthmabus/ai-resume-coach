from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

import worker


USER_ID = "user-123"
ANALYSIS_ID = "analysis-123"
MESSAGE_ID = "message-123"


def conditional_failure() -> ClientError:
    return ClientError(
        {
            "Error": {
                "Code": "ConditionalCheckFailedException",
                "Message": "Condition failed",
            }
        },
        "UpdateItem",
    )


def resume_message() -> dict:
    return {
        "messageId": MESSAGE_ID,
        "body": json.dumps(
            {
                "schemaVersion": 1,
                "jobType": "resumeAnalysis",
                "jobId": ANALYSIS_ID,
                "analysisId": ANALYSIS_ID,
                "userId": USER_ID,
            }
        ),
    }


def resume_item(status="processing") -> dict:
    return {
        "pk": f"USER#{USER_ID}",
        "sk": f"RESUME#{ANALYSIS_ID}",
        "recordType": "resumeAnalysis",
        "userId": USER_ID,
        "analysisId": ANALYSIS_ID,
        "status": status,
        "version": 2,
        "resumeText": "Engineering leader",
        "targetCareer": {
            "roleTitle": "Director",
            "industry": "Technology",
        },
        "provider": "rule-based",
    }


def test_completed_duplicate_is_skipped(monkeypatch):
    table = MagicMock()
    table.get_item.return_value = {
        "Item": resume_item("completed")
    }

    provider_factory = MagicMock()

    monkeypatch.setattr(worker, "table", table)
    monkeypatch.setattr(
        worker,
        "get_analysis_provider",
        provider_factory,
    )

    response = worker.lambda_handler(
        {"Records": [resume_message()]},
        None,
    )

    assert response == {"batchItemFailures": []}

    provider_factory.assert_not_called()
    table.update_item.assert_not_called()


def test_active_claim_duplicate_is_skipped(monkeypatch):
    item = resume_item(
        worker.STATUS_WORKER_PROCESSING
    )
    item["processingLeaseExpiresAt"] = (
        worker.epoch_seconds() + 120
    )

    table = MagicMock()
    table.get_item.return_value = {"Item": item}

    monkeypatch.setattr(worker, "table", table)

    response = worker.lambda_handler(
        {"Records": [resume_message()]},
        None,
    )

    assert response == {"batchItemFailures": []}
    table.update_item.assert_not_called()


def test_first_delivery_claims_before_provider(
    monkeypatch,
):
    original = resume_item("processing")
    claimed = {
        **original,
        "status": worker.STATUS_WORKER_PROCESSING,
        "processingAttemptId": "attempt-123",
        "version": 3,
    }

    table = MagicMock()
    table.get_item.return_value = {
        "Item": original
    }
    table.update_item.side_effect = [
        {"Attributes": claimed},
        {
            "Attributes": {
                **claimed,
                "status": "completed",
                "version": 4,
            }
        },
    ]

    provider = MagicMock()
    provider.analyze.return_value = {
        "provider": "rule-based",
        "model": "",
        "analysisVersion": "test-v1",
        "score": 90,
        "wordCount": 2,
        "dynamicScores": [],
        "roleFitSummary": "Strong fit",
        "roleSpecificGaps": [],
        "strengths": ["Leadership"],
        "recommendations": ["Add metrics"],
        "executiveSummary": "Summary",
    }

    monkeypatch.setattr(worker, "table", table)
    monkeypatch.setattr(
        worker,
        "get_analysis_provider",
        MagicMock(return_value=provider),
    )
    monkeypatch.setattr(
        worker.uuid,
        "uuid4",
        MagicMock(return_value="attempt-123"),
    )

    response = worker.lambda_handler(
        {"Records": [resume_message()]},
        None,
    )

    assert response == {"batchItemFailures": []}
    provider.analyze.assert_called_once()

    first_update = table.update_item.call_args_list[
        0
    ].kwargs

    assert (
        first_update[
            "ExpressionAttributeValues"
        ][":workerProcessing"]
        == worker.STATUS_WORKER_PROCESSING
    )


def test_claim_race_skips_second_worker(
    monkeypatch,
):
    original = resume_item("processing")
    raced = {
        **original,
        "status": worker.STATUS_WORKER_PROCESSING,
        "processingLeaseExpiresAt": (
            worker.epoch_seconds() + 120
        ),
    }

    table = MagicMock()
    table.get_item.side_effect = [
        {"Item": original},
        {"Item": raced},
    ]
    table.update_item.side_effect = (
        conditional_failure()
    )

    provider_factory = MagicMock()

    monkeypatch.setattr(worker, "table", table)
    monkeypatch.setattr(
        worker,
        "get_analysis_provider",
        provider_factory,
    )

    response = worker.lambda_handler(
        {"Records": [resume_message()]},
        None,
    )

    assert response == {"batchItemFailures": []}
    provider_factory.assert_not_called()


def test_failure_returns_only_failed_message(
    monkeypatch,
):
    successful = {
        "messageId": "successful-message",
        "body": json.dumps(
            {
                "jobType": "resumeAnalysis",
                "analysisId": "completed-analysis",
                "userId": USER_ID,
            }
        ),
    }

    failed = {
        "messageId": "failed-message",
        "body": json.dumps(
            {
                "jobType": "resumeAnalysis",
                "analysisId": "failed-analysis",
                "userId": USER_ID,
            }
        ),
    }

    def process_record(record):
        if record["messageId"] == "failed-message":
            raise RuntimeError("Provider failed")

    monkeypatch.setattr(
        worker,
        "process_record",
        process_record,
    )

    response = worker.lambda_handler(
        {"Records": [successful, failed]},
        None,
    )

    assert response == {
        "batchItemFailures": [
            {
                "itemIdentifier": (
                    "failed-message"
                )
            }
        ]
    }


def test_provider_failure_marks_claim_retryable(
    monkeypatch,
):
    original = resume_item("processing")
    claimed = {
        **original,
        "status": worker.STATUS_WORKER_PROCESSING,
        "processingAttemptId": "attempt-123",
        "version": 3,
    }

    table = MagicMock()
    table.get_item.return_value = {
        "Item": original
    }
    table.update_item.side_effect = [
        {"Attributes": claimed},
        {
            "Attributes": {
                **claimed,
                "status": (
                    worker.STATUS_FAILED_RETRYABLE
                ),
            }
        },
    ]

    provider = MagicMock()
    provider.analyze.side_effect = RuntimeError(
        "Provider failed"
    )

    monkeypatch.setattr(worker, "table", table)
    monkeypatch.setattr(
        worker,
        "get_analysis_provider",
        MagicMock(return_value=provider),
    )
    monkeypatch.setattr(
        worker.uuid,
        "uuid4",
        MagicMock(return_value="attempt-123"),
    )

    response = worker.lambda_handler(
        {"Records": [resume_message()]},
        None,
    )

    assert response == {
        "batchItemFailures": [
            {
                "itemIdentifier": MESSAGE_ID,
            }
        ]
    }

    failure_update = table.update_item.call_args_list[
        1
    ].kwargs

    assert (
        failure_update[
            "ExpressionAttributeValues"
        ][":status"]
        == worker.STATUS_FAILED_RETRYABLE
    )


def test_failed_record_emits_worker_failure_metric(
    monkeypatch,
):
    record = {
        "messageId": "failed-message",
        "body": json.dumps(
            {
                "jobType": "resumeAnalysis",
                "analysisId": "analysis-123",
                "userId": "user-123",
            }
        ),
    }

    logger = MagicMock()

    monkeypatch.setattr(worker, "logger", logger)
    monkeypatch.setattr(
        worker,
        "process_record",
        MagicMock(
            side_effect=RuntimeError(
                "Provider failed"
            )
        ),
    )

    response = worker.lambda_handler(
        {"Records": [record]},
        None,
    )

    assert response == {
        "batchItemFailures": [
            {
                "itemIdentifier": "failed-message",
            }
        ]
    }

    metric_messages = [
        call.args[0]
        for call in logger.error.call_args_list
    ]

    assert len(metric_messages) == 1

    metric = json.loads(metric_messages[0])

    assert metric["WorkerRecordFailures"] == 1
    assert metric["MessageId"] == "failed-message"
    assert metric["JobType"] == "resumeAnalysis"
    assert metric["RecordId"] == "analysis-123"
