from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import boto3

from core.outbox_publisher import (
    DynamoDbOutboxRepository,
    OutboxPublisher,
    PublishResult,
    SqsEventPublisher,
)


logger = logging.getLogger(__name__)
logger.setLevel(
    os.getenv("LOG_LEVEL", "INFO").upper()
)


DEFAULT_OUTBOX_BATCH_SIZE = 25
DEFAULT_PROJECT_NAME = "ai-resume-coach"
DEFAULT_ENVIRONMENT = "unknown"

_publisher: OutboxPublisher | None = None


def required_environment_variable(name: str) -> str:
    value = str(os.getenv(name) or "").strip()

    if not value:
        raise RuntimeError(
            f"Required environment variable {name} "
            "is not configured"
        )

    return value


def configured_table_name() -> str:
    """
    Resolve the DynamoDB table name.

    RESUME_ANALYSIS_TABLE matches the existing application and worker
    configuration. DYNAMODB_TABLE_NAME remains supported as a fallback
    for compatibility with earlier infrastructure drafts.
    """
    return (
        str(os.getenv("RESUME_ANALYSIS_TABLE") or "").strip()
        or str(os.getenv("DYNAMODB_TABLE_NAME") or "").strip()
        or required_environment_variable(
            "RESUME_ANALYSIS_TABLE"
        )
    )


def configured_batch_size() -> int:
    raw_value = str(
        os.getenv(
            "OUTBOX_BATCH_SIZE",
            str(DEFAULT_OUTBOX_BATCH_SIZE),
        )
    ).strip()

    try:
        batch_size = int(raw_value)
    except ValueError as error:
        raise RuntimeError(
            "OUTBOX_BATCH_SIZE must be an integer"
        ) from error

    if batch_size <= 0:
        raise RuntimeError(
            "OUTBOX_BATCH_SIZE must be greater than zero"
        )

    return batch_size


def configured_metric_namespace() -> str:
    """
    Build the CloudWatch custom-metric namespace.

    Example:
        ai-resume-coach/dev
    """
    project_name = (
        str(
            os.getenv(
                "PROJECT_NAME",
                DEFAULT_PROJECT_NAME,
            )
        ).strip()
        or DEFAULT_PROJECT_NAME
    )

    environment = (
        str(
            os.getenv(
                "ENVIRONMENT",
                DEFAULT_ENVIRONMENT,
            )
        ).strip()
        or DEFAULT_ENVIRONMENT
    )

    return f"{project_name}/{environment}"


def configured_function_name() -> str:
    """
    Return the Lambda function name used as the EMF dimension.
    """
    return (
        str(
            os.getenv(
                "AWS_LAMBDA_FUNCTION_NAME",
                "",
            )
        ).strip()
        or "outbox-publisher"
    )


def build_publisher() -> OutboxPublisher:
    """
    Build the publisher from Lambda environment configuration.

    AWS clients are deliberately created here instead of at module import
    time. This keeps local imports and unit tests independent of AWS.
    """
    table_name = configured_table_name()
    queue_url = required_environment_variable(
        "RESUME_ANALYSIS_QUEUE_URL"
    )
    region = (
        str(os.getenv("AWS_REGION") or "").strip()
        or str(os.getenv("AWS_DEFAULT_REGION") or "").strip()
        or "unknown"
    )
    batch_size = configured_batch_size()

    dynamodb = boto3.resource("dynamodb")
    sqs = boto3.client("sqs")

    repository = DynamoDbOutboxRepository(
        table=dynamodb.Table(table_name),
        region=region,
    )

    event_publisher = SqsEventPublisher(
        client=sqs,
        queue_url=queue_url,
    )

    return OutboxPublisher(
        repository=repository,
        event_publisher=event_publisher,
        batch_size=batch_size,
    )


def get_publisher() -> OutboxPublisher:
    """
    Reuse the publisher across warm Lambda invocations.
    """
    global _publisher

    if _publisher is None:
        _publisher = build_publisher()

    return _publisher


def reset_publisher() -> None:
    """
    Clear the cached publisher.

    Intended for unit tests and controlled configuration reloads.
    """
    global _publisher
    _publisher = None


def result_payload(
    result: PublishResult,
) -> dict[str, int]:
    return {
        "examined": result.examined,
        "claimed": result.claimed,
        "published": result.published,
        "failed": result.failed,
        "skipped": result.skipped,
    }


def embedded_metric_payload(
    result: PublishResult,
) -> dict[str, Any]:
    """
    Build a CloudWatch Embedded Metric Format payload.

    CloudWatch extracts these metrics directly from the Lambda log event,
    so the Lambda does not require cloudwatch:PutMetricData permission.
    """
    return {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": configured_metric_namespace(),
                    "Dimensions": [
                        [
                            "FunctionName",
                        ]
                    ],
                    "Metrics": [
                        {
                            "Name": "OutboxPublisherCycles",
                            "Unit": "Count",
                        },
                        {
                            "Name": "OutboxEventsExamined",
                            "Unit": "Count",
                        },
                        {
                            "Name": "OutboxEventsClaimed",
                            "Unit": "Count",
                        },
                        {
                            "Name": "OutboxEventsPublished",
                            "Unit": "Count",
                        },
                        {
                            "Name": "OutboxPublishFailures",
                            "Unit": "Count",
                        },
                        {
                            "Name": "OutboxClaimSkips",
                            "Unit": "Count",
                        },
                    ],
                }
            ],
        },
        "FunctionName": configured_function_name(),
        "OutboxPublisherCycles": 1,
        "OutboxEventsExamined": result.examined,
        "OutboxEventsClaimed": result.claimed,
        "OutboxEventsPublished": result.published,
        "OutboxPublishFailures": result.failed,
        "OutboxClaimSkips": result.skipped,
    }


def emit_embedded_metrics(
    result: PublishResult,
) -> None:
    """
    Emit one EMF log event for the completed publisher cycle.
    """
    logger.info(
        json.dumps(
            embedded_metric_payload(result),
            separators=(",", ":"),
        )
    )


def handler(
    event: dict[str, Any] | None,
    context: Any,
) -> dict[str, int]:
    """
    Run one bounded outbox-publishing cycle.

    Unexpected service-level exceptions propagate so Lambda records the
    invocation as failed. Individual transport failures are handled by
    OutboxPublisher and returned through the failed count.
    """
    request_id = getattr(
        context,
        "aws_request_id",
        None,
    )

    trigger_source = (
        event.get(
            "source",
            "manual",
        )
        if isinstance(event, dict)
        else "manual"
    )

    batch_size = configured_batch_size()

    logger.info(
        json.dumps(
            {
                "message": (
                    "Starting outbox publisher invocation"
                ),
                "awsRequestId": request_id,
                "triggerSource": trigger_source,
                "batchSize": batch_size,
            },
            separators=(",", ":"),
        )
    )

    result = get_publisher().publish_pending()
    response = result_payload(result)

    logger.info(
        json.dumps(
            {
                "message": (
                    "Completed outbox publisher invocation"
                ),
                "awsRequestId": request_id,
                **response,
            },
            separators=(",", ":"),
        )
    )

    emit_embedded_metrics(result)

    return response
