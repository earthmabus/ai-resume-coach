from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from core.config import ConfigurationError, get_config
from core.responses import build_response


logger = logging.getLogger(__name__)


def _metadata(config) -> dict[str, str]:
    return {
        "region": config.aws_region,
        "environment": config.environment,
        "deploymentId": config.deployment_id,
        "version": config.app_version,
    }


def live(event: dict[str, Any] | None = None):
    try:
        config = get_config()
    except ConfigurationError:
        # Liveness confirms that the process can execute. It should not
        # depend on readiness configuration or external AWS services.
        return build_response(
            200,
            {
                "status": "alive",
                "check": "liveness",
            },
        )

    return build_response(
        200,
        {
            "status": "alive",
            "check": "liveness",
            **_metadata(config),
        },
    )


def ready(event: dict[str, Any] | None = None):
    checks: dict[str, dict[str, Any]] = {}

    try:
        config = get_config()
        checks["configuration"] = {"status": "pass"}
    except ConfigurationError as exc:
        logger.error(
            "Readiness configuration check failed",
            extra={
                "check": "configuration",
                "errorType": type(exc).__name__,
            },
        )

        return build_response(
            503,
            {
                "status": "not-ready",
                "check": "readiness",
                "checks": {
                    "configuration": {"status": "fail"},
                },
            },
        )

    try:
        dynamodb = boto3.client("dynamodb")
        dynamodb.describe_table(TableName=config.table_name)

        checks["dynamodb"] = {"status": "pass"}
    except (BotoCoreError, ClientError) as exc:
        logger.error(
            "DynamoDB readiness check failed",
            extra={
                "check": "dynamodb",
                "region": config.aws_region,
                "errorType": type(exc).__name__,
            },
        )

        checks["dynamodb"] = {"status": "fail"}

    try:
        sqs = boto3.client("sqs")
        sqs.get_queue_attributes(
            QueueUrl=config.processing_queue_url,
            AttributeNames=["QueueArn"],
        )

        checks["sqs"] = {"status": "pass"}
    except (BotoCoreError, ClientError) as exc:
        logger.error(
            "SQS readiness check failed",
            extra={
                "check": "sqs",
                "region": config.aws_region,
                "errorType": type(exc).__name__,
            },
        )

        checks["sqs"] = {"status": "fail"}

    is_ready = all(
        check["status"] == "pass"
        for check in checks.values()
    )

    return build_response(
        200 if is_ready else 503,
        {
            "status": "ready" if is_ready else "not-ready",
            "check": "readiness",
            **_metadata(config),
            "checks": checks,
        },
    )
