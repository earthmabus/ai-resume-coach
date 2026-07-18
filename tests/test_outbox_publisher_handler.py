from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import outbox_publisher_handler
from core.outbox_publisher import PublishResult


def test_handler_publishes_pending_events(
    monkeypatch,
):
    publisher = MagicMock()

    publisher.publish_pending.return_value = PublishResult(
        examined=5,
        claimed=4,
        published=3,
        failed=1,
        skipped=1,
    )

    monkeypatch.setattr(
        outbox_publisher_handler,
        "get_publisher",
        MagicMock(return_value=publisher),
    )

    response = outbox_publisher_handler.handler(
        {
            "source": "manual-test",
        },
        SimpleNamespace(
            aws_request_id="request-123",
        ),
    )

    assert response == {
        "examined": 5,
        "claimed": 4,
        "published": 3,
        "failed": 1,
        "skipped": 1,
        "permanentlyFailed": 0,
    }

    publisher.publish_pending.assert_called_once_with()


def test_handler_returns_zero_counts_for_empty_batch(
    monkeypatch,
):
    publisher = MagicMock()
    publisher.publish_pending.return_value = PublishResult()

    monkeypatch.setattr(
        outbox_publisher_handler,
        "get_publisher",
        MagicMock(return_value=publisher),
    )

    response = outbox_publisher_handler.handler(
        {},
        None,
    )

    assert response == {
        "examined": 0,
        "claimed": 0,
        "published": 0,
        "failed": 0,
        "skipped": 0,
        "permanentlyFailed": 0,
    }


def test_handler_accepts_none_event(
    monkeypatch,
):
    publisher = MagicMock()
    publisher.publish_pending.return_value = PublishResult()

    monkeypatch.setattr(
        outbox_publisher_handler,
        "get_publisher",
        MagicMock(return_value=publisher),
    )

    response = outbox_publisher_handler.handler(
        None,
        None,
    )

    assert response == {
        "examined": 0,
        "claimed": 0,
        "published": 0,
        "failed": 0,
        "skipped": 0,
        "permanentlyFailed": 0,
    }


def test_handler_propagates_unexpected_publisher_failure(
    monkeypatch,
):
    publisher = MagicMock()
    publisher.publish_pending.side_effect = RuntimeError(
        "DynamoDB unavailable"
    )

    monkeypatch.setattr(
        outbox_publisher_handler,
        "get_publisher",
        MagicMock(return_value=publisher),
    )

    with pytest.raises(
        RuntimeError,
        match="DynamoDB unavailable",
    ):
        outbox_publisher_handler.handler(
            {},
            SimpleNamespace(
                aws_request_id="request-456",
            ),
        )


def test_configured_table_name_uses_existing_variable(
    monkeypatch,
):
    monkeypatch.setenv(
        "RESUME_ANALYSIS_TABLE",
        "primary-table",
    )
    monkeypatch.setenv(
        "DYNAMODB_TABLE_NAME",
        "fallback-table",
    )

    assert (
        outbox_publisher_handler.configured_table_name()
        == "primary-table"
    )


def test_configured_table_name_supports_draft_fallback(
    monkeypatch,
):
    monkeypatch.delenv(
        "RESUME_ANALYSIS_TABLE",
        raising=False,
    )
    monkeypatch.setenv(
        "DYNAMODB_TABLE_NAME",
        "fallback-table",
    )

    assert (
        outbox_publisher_handler.configured_table_name()
        == "fallback-table"
    )


def test_configured_table_name_is_required(
    monkeypatch,
):
    monkeypatch.delenv(
        "RESUME_ANALYSIS_TABLE",
        raising=False,
    )
    monkeypatch.delenv(
        "DYNAMODB_TABLE_NAME",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Required environment variable "
            "RESUME_ANALYSIS_TABLE is not configured"
        ),
    ):
        outbox_publisher_handler.configured_table_name()


@pytest.mark.parametrize(
    "configured_value",
    [
        "0",
        "-1",
        "not-a-number",
    ],
)
def test_configured_batch_size_rejects_invalid_values(
    monkeypatch,
    configured_value,
):
    monkeypatch.setenv(
        "OUTBOX_BATCH_SIZE",
        configured_value,
    )

    with pytest.raises(
        RuntimeError,
        match="OUTBOX_BATCH_SIZE",
    ):
        outbox_publisher_handler.configured_batch_size()


def test_configured_metric_namespace_uses_project_and_environment(
    monkeypatch,
):
    monkeypatch.setenv(
        "PROJECT_NAME",
        "resume-platform",
    )
    monkeypatch.setenv(
        "ENVIRONMENT",
        "production",
    )

    assert (
        outbox_publisher_handler.configured_metric_namespace()
        == "resume-platform/production"
    )


def test_configured_metric_namespace_uses_defaults(
    monkeypatch,
):
    monkeypatch.delenv(
        "PROJECT_NAME",
        raising=False,
    )
    monkeypatch.delenv(
        "ENVIRONMENT",
        raising=False,
    )

    assert (
        outbox_publisher_handler.configured_metric_namespace()
        == "ai-resume-coach/unknown"
    )


def test_configured_regional_processing_queue_names_parses_json(
    monkeypatch,
):
    monkeypatch.setenv(
        "REGIONAL_PROCESSING_QUEUE_NAMES",
        json.dumps(
            {
                "us-east-1": "east-processing",
                "us-west-2": "west-processing",
                " ": "ignored",
                "us-east-2": "",
            }
        ),
    )

    assert (
        outbox_publisher_handler.configured_regional_processing_queue_names()
        == {
            "us-east-1": "east-processing",
            "us-west-2": "west-processing",
        }
    )


@pytest.mark.parametrize(
    "configured_value",
    [
        "[\"east-processing\"]",
        "{not-json",
    ],
)
def test_configured_regional_processing_queue_names_requires_json_object(
    monkeypatch,
    configured_value,
):
    monkeypatch.setenv(
        "REGIONAL_PROCESSING_QUEUE_NAMES",
        configured_value,
    )

    with pytest.raises(
        RuntimeError,
        match="REGIONAL_PROCESSING_QUEUE_NAMES",
    ):
        outbox_publisher_handler.configured_regional_processing_queue_names()


def test_configured_function_name_uses_lambda_environment(
    monkeypatch,
):
    monkeypatch.setenv(
        "AWS_LAMBDA_FUNCTION_NAME",
        "publisher-function",
    )

    assert (
        outbox_publisher_handler.configured_function_name()
        == "publisher-function"
    )


def test_configured_function_name_uses_fallback(
    monkeypatch,
):
    monkeypatch.delenv(
        "AWS_LAMBDA_FUNCTION_NAME",
        raising=False,
    )

    assert (
        outbox_publisher_handler.configured_function_name()
        == "outbox-publisher"
    )


def test_embedded_metric_payload_contains_expected_metrics(
    monkeypatch,
):
    monkeypatch.setenv(
        "PROJECT_NAME",
        "ai-resume-coach",
    )
    monkeypatch.setenv(
        "ENVIRONMENT",
        "dev",
    )
    monkeypatch.setenv(
        "AWS_LAMBDA_FUNCTION_NAME",
        "ai-resume-coach-dev-outbox-publisher",
    )

    monkeypatch.setattr(
        outbox_publisher_handler.time,
        "time",
        MagicMock(return_value=1234.567),
    )

    result = PublishResult(
        examined=5,
        claimed=4,
        published=3,
        failed=1,
        skipped=1,
    )

    payload = (
        outbox_publisher_handler.embedded_metric_payload(
            result
        )
    )

    assert payload["_aws"]["Timestamp"] == 1234567

    metric_definition = payload["_aws"][
        "CloudWatchMetrics"
    ][0]

    assert metric_definition["Namespace"] == (
        "ai-resume-coach/dev"
    )
    assert metric_definition["Dimensions"] == [
        ["FunctionName"]
    ]

    metric_names = {
        metric["Name"]
        for metric in metric_definition["Metrics"]
    }

    assert metric_names == {
        "OutboxPublisherCycles",
        "OutboxEventsExamined",
        "OutboxEventsClaimed",
        "OutboxEventsPublished",
        "OutboxPublishFailures",
        "OutboxClaimSkips",
        "OutboxPermanentFailures",
    }

    assert payload["FunctionName"] == (
        "ai-resume-coach-dev-outbox-publisher"
    )
    assert payload["OutboxPublisherCycles"] == 1
    assert payload["OutboxEventsExamined"] == 5
    assert payload["OutboxEventsClaimed"] == 4
    assert payload["OutboxEventsPublished"] == 3
    assert payload["OutboxPublishFailures"] == 1
    assert payload["OutboxClaimSkips"] == 1


def test_empty_batch_still_emits_heartbeat_metrics(
    monkeypatch,
):
    monkeypatch.setenv(
        "PROJECT_NAME",
        "ai-resume-coach",
    )
    monkeypatch.setenv(
        "ENVIRONMENT",
        "dev",
    )

    payload = (
        outbox_publisher_handler.embedded_metric_payload(
            PublishResult()
        )
    )

    assert payload["OutboxPublisherCycles"] == 1
    assert payload["OutboxEventsExamined"] == 0
    assert payload["OutboxEventsClaimed"] == 0
    assert payload["OutboxEventsPublished"] == 0
    assert payload["OutboxPublishFailures"] == 0
    assert payload["OutboxClaimSkips"] == 0


def test_emit_embedded_metrics_logs_valid_json(
    monkeypatch,
):
    log_info = MagicMock()

    monkeypatch.setattr(
        outbox_publisher_handler.logger,
        "info",
        log_info,
    )

    result = PublishResult(
        examined=2,
        claimed=2,
        published=1,
        failed=1,
        skipped=0,
    )

    outbox_publisher_handler.emit_embedded_metrics(
        result
    )

    log_info.assert_called_once()

    logged_payload = json.loads(
        log_info.call_args.args[0]
    )

    assert logged_payload["OutboxEventsExamined"] == 2
    assert logged_payload["OutboxEventsClaimed"] == 2
    assert logged_payload["OutboxEventsPublished"] == 1
    assert logged_payload["OutboxPublishFailures"] == 1


def test_handler_emits_metrics_after_successful_cycle(
    monkeypatch,
):
    result = PublishResult(
        examined=3,
        claimed=2,
        published=2,
        failed=0,
        skipped=1,
    )

    publisher = MagicMock()
    publisher.publish_pending.return_value = result

    emit_metrics = MagicMock()

    monkeypatch.setattr(
        outbox_publisher_handler,
        "get_publisher",
        MagicMock(return_value=publisher),
    )
    monkeypatch.setattr(
        outbox_publisher_handler,
        "emit_embedded_metrics",
        emit_metrics,
    )

    response = outbox_publisher_handler.handler(
        {
            "source": "scheduled-test",
        },
        SimpleNamespace(
            aws_request_id="request-789",
        ),
    )

    assert response == {
        "examined": 3,
        "claimed": 2,
        "published": 2,
        "failed": 0,
        "skipped": 1,
        "permanentlyFailed": 0,
    }

    emit_metrics.assert_called_once_with(result)


def test_handler_does_not_emit_success_metrics_when_publisher_raises(
    monkeypatch,
):
    publisher = MagicMock()
    publisher.publish_pending.side_effect = RuntimeError(
        "publisher failed"
    )

    emit_metrics = MagicMock()

    monkeypatch.setattr(
        outbox_publisher_handler,
        "get_publisher",
        MagicMock(return_value=publisher),
    )
    monkeypatch.setattr(
        outbox_publisher_handler,
        "emit_embedded_metrics",
        emit_metrics,
    )

    with pytest.raises(
        RuntimeError,
        match="publisher failed",
    ):
        outbox_publisher_handler.handler(
            {},
            SimpleNamespace(
                aws_request_id="request-error",
            ),
        )

    emit_metrics.assert_not_called()


def test_build_publisher_uses_expected_aws_resources(
    monkeypatch,
):
    monkeypatch.setenv(
        "RESUME_ANALYSIS_TABLE",
        "test-outbox-table",
    )
    monkeypatch.setenv(
        "RESUME_ANALYSIS_QUEUE_URL",
        "https://sqs.example/test-queue",
    )
    monkeypatch.setenv(
        "AWS_REGION",
        "us-east-1",
    )
    monkeypatch.setenv(
        "OUTBOX_BATCH_SIZE",
        "10",
    )

    table = MagicMock()
    dynamodb = MagicMock()
    dynamodb.Table.return_value = table
    sqs = MagicMock()

    resource = MagicMock(return_value=dynamodb)
    client = MagicMock(return_value=sqs)

    monkeypatch.setattr(
        outbox_publisher_handler.boto3,
        "resource",
        resource,
    )
    monkeypatch.setattr(
        outbox_publisher_handler.boto3,
        "client",
        client,
    )

    publisher = (
        outbox_publisher_handler.build_publisher()
    )

    assert publisher is not None

    resource.assert_called_once_with("dynamodb")
    dynamodb.Table.assert_called_once_with(
        "test-outbox-table"
    )
    client.assert_called_once_with("sqs")


def test_get_publisher_caches_warm_invocation_instance(
    monkeypatch,
):
    built_publisher = MagicMock()
    builder = MagicMock(
        return_value=built_publisher
    )

    monkeypatch.setattr(
        outbox_publisher_handler,
        "build_publisher",
        builder,
    )

    outbox_publisher_handler.reset_publisher()

    first = outbox_publisher_handler.get_publisher()
    second = outbox_publisher_handler.get_publisher()

    assert first is built_publisher
    assert second is built_publisher
    builder.assert_called_once_with()

    outbox_publisher_handler.reset_publisher()

def test_configured_max_workers_uses_default(
    monkeypatch,
):
    monkeypatch.delenv(
        "OUTBOX_MAX_WORKERS",
        raising=False,
    )

    assert (
        outbox_publisher_handler.configured_max_workers()
        == 4
    )


def test_configured_max_workers_uses_configured_value(
    monkeypatch,
):
    monkeypatch.setenv(
        "OUTBOX_MAX_WORKERS",
        "8",
    )

    assert (
        outbox_publisher_handler.configured_max_workers()
        == 8
    )


@pytest.mark.parametrize(
    "configured_value",
    [
        "0",
        "-1",
        "not-a-number",
    ],
)
def test_configured_max_workers_rejects_invalid_values(
    monkeypatch,
    configured_value,
):
    monkeypatch.setenv(
        "OUTBOX_MAX_WORKERS",
        configured_value,
    )

    with pytest.raises(
        RuntimeError,
        match="OUTBOX_MAX_WORKERS",
    ):
        (
            outbox_publisher_handler
            .configured_max_workers()
        )


def test_build_publisher_passes_configured_max_workers(
    monkeypatch,
):
    monkeypatch.setenv(
        "RESUME_ANALYSIS_TABLE",
        "test-outbox-table",
    )
    monkeypatch.setenv(
        "RESUME_ANALYSIS_QUEUE_URL",
        "https://sqs.example/test-queue",
    )
    monkeypatch.setenv(
        "AWS_REGION",
        "us-east-1",
    )
    monkeypatch.setenv(
        "OUTBOX_BATCH_SIZE",
        "10",
    )
    monkeypatch.setenv(
        "OUTBOX_MAX_WORKERS",
        "6",
    )

    table = MagicMock()
    dynamodb = MagicMock()
    dynamodb.Table.return_value = table
    sqs = MagicMock()

    monkeypatch.setattr(
        outbox_publisher_handler.boto3,
        "resource",
        MagicMock(return_value=dynamodb),
    )
    monkeypatch.setattr(
        outbox_publisher_handler.boto3,
        "client",
        MagicMock(return_value=sqs),
    )

    publisher_constructor = MagicMock(
        return_value=MagicMock()
    )

    monkeypatch.setattr(
        outbox_publisher_handler,
        "OutboxPublisher",
        publisher_constructor,
    )

    outbox_publisher_handler.build_publisher()

    publisher_constructor.assert_called_once()

    arguments = publisher_constructor.call_args.kwargs

    assert arguments["batch_size"] == 10
    assert arguments["max_workers"] == 6


def test_handler_start_log_includes_max_workers(
    monkeypatch,
):
    publisher = MagicMock()
    publisher.publish_pending.return_value = (
        PublishResult()
    )

    log_info = MagicMock()

    monkeypatch.setenv(
        "OUTBOX_BATCH_SIZE",
        "25",
    )
    monkeypatch.setenv(
        "OUTBOX_MAX_WORKERS",
        "4",
    )
    monkeypatch.setattr(
        outbox_publisher_handler,
        "get_publisher",
        MagicMock(return_value=publisher),
    )
    monkeypatch.setattr(
        outbox_publisher_handler.logger,
        "info",
        log_info,
    )
    monkeypatch.setattr(
        outbox_publisher_handler,
        "emit_embedded_metrics",
        MagicMock(),
    )

    outbox_publisher_handler.handler(
        {
            "source": "scheduled-test",
        },
        SimpleNamespace(
            aws_request_id="request-123",
        ),
    )

    starting_log = json.loads(
        log_info.call_args_list[0].args[0]
    )

    assert starting_log["batchSize"] == 25
    assert starting_log["maxWorkers"] == 4


def test_configured_max_delivery_attempts_uses_default(monkeypatch):
    monkeypatch.delenv(
        "OUTBOX_MAX_DELIVERY_ATTEMPTS",
        raising=False,
    )
    assert (
        outbox_publisher_handler.configured_max_delivery_attempts()
        == 20
    )


def test_configured_delivered_retention_seconds_uses_default(monkeypatch):
    monkeypatch.delenv(
        "OUTBOX_DELIVERED_RETENTION_SECONDS",
        raising=False,
    )
    assert (
        outbox_publisher_handler.configured_delivered_retention_seconds()
        == 2592000
    )


def test_embedded_metrics_include_permanent_failures(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", "ai-resume-coach")
    monkeypatch.setenv("ENVIRONMENT", "dev")
    result = PublishResult(
        examined=1,
        claimed=1,
        failed=1,
        permanently_failed=1,
    )

    payload = outbox_publisher_handler.embedded_metric_payload(result)

    assert payload["OutboxPermanentFailures"] == 1
    names = {
        metric["Name"]
        for metric in payload["_aws"]["CloudWatchMetrics"][0]["Metrics"]
    }
    assert "OutboxPermanentFailures" in names
