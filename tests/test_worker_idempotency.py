from __future__ import annotations

import json
import logging
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


def traced_resume_message() -> dict:
    return {
        "messageId": MESSAGE_ID,
        "body": json.dumps(
            {
                "schemaVersion": 1,
                "eventType": "RESUME_ANALYSIS_REQUESTED",
                "jobType": "resumeAnalysis",
                "jobId": ANALYSIS_ID,
                "analysisId": ANALYSIS_ID,
                "userId": USER_ID,
                "requestId": "request-123",
                "correlationId": "correlation-123",
                "outboxEventId": "outbox-123",
                "ownerRegion": "us-east-1",
                "sourceRegion": "us-west-2",
                "sourceDeploymentId": "deployment-west",
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


def test_worker_message_context_normalizes_safe_identifiers():
    record = traced_resume_message()
    body = json.loads(record["body"])

    context = worker.build_worker_message_context(
        record=record,
        body=body,
        runtime_invocation_id="lambda-request-123",
    )

    assert context.request_id == "request-123"
    assert context.correlation_id == "correlation-123"
    assert context.work_id == ANALYSIS_ID
    assert context.outbox_event_id == "outbox-123"
    assert context.transport_message_id == MESSAGE_ID
    assert context.runtime_invocation_id == "lambda-request-123"
    assert context.owner_region == "us-east-1"
    assert context.source_region == "us-west-2"
    assert context.event_type == "RESUME_ANALYSIS_REQUESTED"


def test_worker_context_uses_request_id_for_legacy_correlation():
    record = resume_message()
    body = json.loads(record["body"])
    body["requestId"] = "request-legacy"

    context = worker.build_worker_message_context(
        record=record,
        body=body,
    )

    assert context.request_id == "request-legacy"
    assert context.correlation_id == "request-legacy"


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


def test_duplicate_skip_log_contains_safe_correlation_fields(
    monkeypatch,
    caplog,
):
    item = resume_item("completed")
    table = MagicMock()
    table.get_item.return_value = {"Item": item}

    monkeypatch.setattr(worker, "table", table)

    record = traced_resume_message()
    with caplog.at_level(logging.INFO):
        worker.process_record(
            record,
            runtime_invocation_id="lambda-request-123",
        )

    log_payloads = [
        json.loads(record.message)
        for record in caplog.records
        if record.message.startswith("{")
    ]

    diagnostic = next(
        payload for payload in log_payloads
        if payload.get("result") == "SKIPPED"
    )

    assert diagnostic["requestId"] == "request-123"
    assert diagnostic["correlationId"] == "correlation-123"
    assert diagnostic["workId"] == ANALYSIS_ID
    assert diagnostic["outboxEventId"] == "outbox-123"
    assert diagnostic["transportMessageId"] == MESSAGE_ID
    assert diagnostic["runtimeInvocationId"] == "lambda-request-123"
    assert diagnostic["ownerRegion"] == "us-east-1"
    assert diagnostic["sourceRegion"] == "us-west-2"
    assert "resumeText" not in diagnostic


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
    assert "runtimeInvocationId" not in first_update["UpdateExpression"]


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

    def process_record(record, *, runtime_invocation_id=None):
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
                "requestId": "request-123",
                "correlationId": "correlation-123",
                "outboxEventId": "outbox-123",
                "ownerRegion": "us-east-1",
                "sourceRegion": "us-west-2",
                "resumeText": "sensitive resume content",
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
    assert metric["RequestId"] == "request-123"
    assert metric["CorrelationId"] == "correlation-123"
    assert metric["OutboxEventId"] == "outbox-123"
    assert metric["OwnerRegion"] == "us-east-1"
    assert metric["SourceRegion"] == "us-west-2"
    assert "sensitive resume content" not in metric_messages[0]
    dimensions = metric["_aws"]["CloudWatchMetrics"][0]["Dimensions"]
    assert dimensions == [["FunctionName"]]
