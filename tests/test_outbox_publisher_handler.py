from __future__ import annotations

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
        "published": 3,
        "failed": 1,
        "skipped": 1,
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
        "published": 0,
        "failed": 0,
        "skipped": 0,
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
