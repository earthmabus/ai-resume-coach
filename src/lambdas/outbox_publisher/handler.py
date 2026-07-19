from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import boto3

from core.config import get_config
from core.outbox_publisher import (
    DEFAULT_MAX_DELIVERY_ATTEMPTS,
    DEFAULT_MAX_WORKERS,
    DEFAULT_DELIVERED_RETENTION_SECONDS,
    DynamoDbOutboxRepository,
    OutboxPublisher,
    PlacementAwareEventPublisher,
    PublishResult,
    SqsEventPublisher,
)
from core.region_routing import RegionRoutingService
from core.regional_transport import SqsRegionalTransport
from core.workflow_dispatch import (
    ResumeWorkflowDispatcher,
    WorkflowDispatchResult,
)
from core.work_placement import (
    WorkOwnershipResolver,
    WorkPlacementService,
)


logger = logging.getLogger(__name__)
logger.setLevel(
    os.getenv(
        "LOG_LEVEL",
        "INFO",
    ).upper()
)


DEFAULT_OUTBOX_BATCH_SIZE = 25
DEFAULT_PROJECT_NAME = "ai-resume-coach"
DEFAULT_ENVIRONMENT = "unknown"

_publisher: OutboxPublisher | None = None
_workflow_dispatcher: ResumeWorkflowDispatcher | None = None


def required_environment_variable(
    name: str,
) -> str:
    value = str(
        os.getenv(name) or ""
    ).strip()

    if not value:
        raise RuntimeError(
            f"Required environment variable "
            f"{name} is not configured"
        )

    return value


def configured_table_name() -> str:
    """
    Resolve the DynamoDB table name.

    RESUME_ANALYSIS_TABLE matches the existing application and worker
    configuration. DYNAMODB_TABLE_NAME remains supported as a fallback.
    """
    return (
        str(
            os.getenv(
                "RESUME_ANALYSIS_TABLE"
            )
            or ""
        ).strip()
        or str(
            os.getenv(
                "DYNAMODB_TABLE_NAME"
            )
            or ""
        ).strip()
        or required_environment_variable(
            "RESUME_ANALYSIS_TABLE"
        )
    )


def configured_positive_integer(
    *,
    environment_variable: str,
    default_value: int,
) -> int:
    raw_value = str(
        os.getenv(
            environment_variable,
            str(default_value),
        )
    ).strip()

    try:
        value = int(raw_value)
    except ValueError as error:
        raise RuntimeError(
            f"{environment_variable} "
            "must be an integer"
        ) from error

    if value <= 0:
        raise RuntimeError(
            f"{environment_variable} "
            "must be greater than zero"
        )

    return value


def configured_batch_size() -> int:
    return configured_positive_integer(
        environment_variable=(
            "OUTBOX_BATCH_SIZE"
        ),
        default_value=(
            DEFAULT_OUTBOX_BATCH_SIZE
        ),
    )


def configured_max_workers() -> int:
    return configured_positive_integer(
        environment_variable=(
            "OUTBOX_MAX_WORKERS"
        ),
        default_value=(
            DEFAULT_MAX_WORKERS
        ),
    )


def configured_max_delivery_attempts() -> int:
    return configured_positive_integer(
        environment_variable=(
            "OUTBOX_MAX_DELIVERY_ATTEMPTS"
        ),
        default_value=(
            DEFAULT_MAX_DELIVERY_ATTEMPTS
        ),
    )


def configured_delivered_retention_seconds() -> int:
    return configured_positive_integer(
        environment_variable=(
            "OUTBOX_DELIVERED_RETENTION_SECONDS"
        ),
        default_value=(
            DEFAULT_DELIVERED_RETENTION_SECONDS
        ),
    )


def configured_metric_namespace() -> str:
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

    return (
        f"{project_name}/{environment}"
    )


def configured_regional_processing_queue_names() -> dict[str, str]:
    return dict(
        get_config().regional_processing_queue_names
    )


def configured_function_name() -> str:
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
    """
    table_name = configured_table_name()
    queue_url = (
        required_environment_variable(
            "RESUME_ANALYSIS_QUEUE_URL"
        )
    )
    region = (
        str(
            os.getenv("AWS_REGION")
            or ""
        ).strip()
        or str(
            os.getenv(
                "AWS_DEFAULT_REGION"
            )
            or ""
        ).strip()
        or "unknown"
    )
    batch_size = configured_batch_size()
    max_workers = configured_max_workers()
    max_delivery_attempts = configured_max_delivery_attempts()
    delivered_retention_seconds = (
        configured_delivered_retention_seconds()
    )

    dynamodb = boto3.resource(
        "dynamodb"
    )
    sqs = boto3.client("sqs")

    repository = (
        DynamoDbOutboxRepository(
            table=dynamodb.Table(
                table_name
            ),
            region=region,
            deployment_id=str(
                os.getenv("DEPLOYMENT_ID")
                or "unknown"
            ),
            delivered_retention_seconds=(
                delivered_retention_seconds
            ),
        )
    )

    event_publisher = SqsEventPublisher(
        client=sqs,
        queue_url=queue_url,
    )
    routing_service = RegionRoutingService()
    placement_service = WorkPlacementService(
        ownership_resolver=WorkOwnershipResolver(
            routing_service.topology
        ),
        routing_service=routing_service,
    )
    regional_transport = SqsRegionalTransport(
        client_factory=(
            lambda owner_region: boto3.client(
                "sqs",
                region_name=owner_region,
            )
        ),
        queue_names_by_region=(
            configured_regional_processing_queue_names()
        ),
    )
    placement_aware_publisher = (
        PlacementAwareEventPublisher(
            local_publisher=event_publisher,
            regional_transport=regional_transport,
            placement_service=placement_service,
        )
    )

    return OutboxPublisher(
        repository=repository,
        event_publisher=placement_aware_publisher,
        batch_size=batch_size,
        max_workers=max_workers,
        max_delivery_attempts=(
            max_delivery_attempts
        ),
    )


def build_workflow_dispatcher() -> ResumeWorkflowDispatcher:
    region = str(os.getenv("AWS_REGION") or "unknown")
    dynamodb = boto3.resource("dynamodb")
    return ResumeWorkflowDispatcher(
        table=dynamodb.Table(configured_table_name()),
        sqs_client=boto3.client("sqs"),
        queue_url=required_environment_variable(
            "RESUME_ANALYSIS_QUEUE_URL"
        ),
        region=region,
        deployment_id=str(os.getenv("DEPLOYMENT_ID") or "unknown"),
        batch_size=configured_batch_size(),
    )


def get_workflow_dispatcher() -> ResumeWorkflowDispatcher:
    global _workflow_dispatcher
    if _workflow_dispatcher is None:
        _workflow_dispatcher = build_workflow_dispatcher()
    return _workflow_dispatcher


def workflow_dispatch_enabled() -> bool:
    configured = os.getenv("WORKFLOW_DISPATCH_ENABLED")
    if configured is not None:
        return configured.strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    # Unit tests use ENVIRONMENT=test and historically exercise only the
    # transactional-outbox publisher. Keep that boundary isolated unless a
    # test explicitly enables aggregate workflow dispatch. Runtime
    # environments remain enabled by default.
    return str(os.getenv("ENVIRONMENT") or "").strip().lower() != "test"


def get_publisher() -> OutboxPublisher:
    global _publisher

    if _publisher is None:
        _publisher = build_publisher()

    return _publisher


def reset_publisher() -> None:
    global _publisher, _workflow_dispatcher
    _publisher = None
    _workflow_dispatcher = None


def result_payload(
    result: PublishResult,
) -> dict[str, int]:
    return {
        "examined": result.examined,
        "claimed": result.claimed,
        "published": result.published,
        "failed": result.failed,
        "skipped": result.skipped,
        "permanentlyFailed": (
            result.permanently_failed
        ),
    }


def embedded_metric_payload(
    result: PublishResult,
) -> dict[str, Any]:
    return {
        "_aws": {
            "Timestamp": int(
                time.time() * 1000
            ),
            "CloudWatchMetrics": [
                {
                    "Namespace": (
                        configured_metric_namespace()
                    ),
                    "Dimensions": [
                        [
                            "FunctionName",
                        ]
                    ],
                    "Metrics": [
                        {
                            "Name": (
                                "OutboxPublisherCycles"
                            ),
                            "Unit": "Count",
                        },
                        {
                            "Name": (
                                "OutboxEventsExamined"
                            ),
                            "Unit": "Count",
                        },
                        {
                            "Name": (
                                "OutboxEventsClaimed"
                            ),
                            "Unit": "Count",
                        },
                        {
                            "Name": (
                                "OutboxEventsPublished"
                            ),
                            "Unit": "Count",
                        },
                        {
                            "Name": (
                                "OutboxPublishFailures"
                            ),
                            "Unit": "Count",
                        },
                        {
                            "Name": (
                                "OutboxClaimSkips"
                            ),
                            "Unit": "Count",
                        },
                        {
                            "Name": (
                                "OutboxPermanentFailures"
                            ),
                            "Unit": "Count",
                        },
                    ],
                }
            ],
        },
        "FunctionName": (
            configured_function_name()
        ),
        "OutboxPublisherCycles": 1,
        "OutboxEventsExamined": (
            result.examined
        ),
        "OutboxEventsClaimed": (
            result.claimed
        ),
        "OutboxEventsPublished": (
            result.published
        ),
        "OutboxPublishFailures": (
            result.failed
        ),
        "OutboxClaimSkips": (
            result.skipped
        ),
        "OutboxPermanentFailures": (
            result.permanently_failed
        ),
    }


def emit_embedded_metrics(
    result: PublishResult,
) -> None:
    logger.info(
        json.dumps(
            embedded_metric_payload(
                result
            ),
            separators=(",", ":"),
        )
    )


def handler(
    event: dict[str, Any] | None,
    context: Any,
) -> dict[str, int]:
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
        if isinstance(
            event,
            dict,
        )
        else "manual"
    )

    batch_size = configured_batch_size()
    max_workers = configured_max_workers()
    max_delivery_attempts = (
        configured_max_delivery_attempts()
    )

    logger.info(
        json.dumps(
            {
                "message": (
                    "Starting outbox "
                    "publisher invocation"
                ),
                "awsRequestId": (
                    request_id
                ),
                "runtimeInvocationId": (
                    request_id
                ),
                "triggerSource": (
                    trigger_source
                ),
                "region": str(os.getenv("AWS_REGION") or "unknown"),
                "currentRegion": str(
                    os.getenv("AWS_REGION") or "unknown"
                ),
                "deploymentId": str(
                    os.getenv("DEPLOYMENT_ID") or "unknown"
                ),
                "environment": str(
                    os.getenv("ENVIRONMENT") or "unknown"
                ),
                "batchSize": batch_size,
                "maxWorkers": max_workers,
                "maxDeliveryAttempts": (
                    max_delivery_attempts
                ),
            },
            separators=(",", ":"),
        )
    )

    result = get_publisher().publish_pending()
    response = result_payload(result)

    if workflow_dispatch_enabled():
        workflow_result = (
            get_workflow_dispatcher().dispatch_pending()
        )
        response["workflow"] = {
            "examined": workflow_result.examined,
            "claimed": workflow_result.claimed,
            "dispatched": workflow_result.dispatched,
            "failed": workflow_result.failed,
            "skipped": workflow_result.skipped,
            "recovered": workflow_result.recovered,
            "recoverySkipped": workflow_result.recovery_skipped,
        }

    logger.info(
        json.dumps(
            {
                "message": (
                    "Completed outbox "
                    "publisher invocation"
                ),
                "awsRequestId": (
                    request_id
                ),
                "runtimeInvocationId": (
                    request_id
                ),
                **response,
            },
            separators=(",", ":"),
        )
    )

    emit_embedded_metrics(result)

    return response
