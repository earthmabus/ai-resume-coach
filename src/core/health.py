from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from core.config import ConfigurationError, get_config
from core.regional_health import (
    HealthReasonCode,
    observations_from_checks,
    RegionalHealthAssessment,
    RegionalHealthStatus,
    classify_readiness_health,
)
from core.responses import build_response


logger = logging.getLogger(__name__)

READINESS_CONNECT_TIMEOUT_SECONDS = 1
READINESS_READ_TIMEOUT_SECONDS = 1
READINESS_MAX_ATTEMPTS = 1

READINESS_CLIENT_CONFIG = Config(
    connect_timeout=READINESS_CONNECT_TIMEOUT_SECONDS,
    read_timeout=READINESS_READ_TIMEOUT_SECONDS,
    retries={
        "max_attempts": READINESS_MAX_ATTEMPTS,
        "mode": "standard",
    },
)


def _metadata(config) -> dict[str, str]:
    return {
        "region": config.aws_region,
        "currentRegion": config.aws_region,
        "siteName": config.site_name,
        "regionRole": config.region_role,
        "environment": config.environment,
        "deploymentId": config.deployment_id,
        "version": config.app_version,
    }


def _regional_health(
    *,
    config,
    checks: dict[str, dict[str, Any]],
    evaluated_at: datetime,
) -> RegionalHealthAssessment:
    return classify_readiness_health(
        checks=checks,
        current_region=config.aws_region,
        site_name=config.site_name,
        region_role=config.region_role,
        environment=config.environment,
        deployment_id=config.deployment_id,
        evaluated_at=evaluated_at,
    )


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
        evaluated_at = datetime.now(timezone.utc)
        observations = observations_from_checks(
            checks={"configuration": {"status": "fail"}},
            observed_at=evaluated_at,
        )
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
                "regionalHealth": RegionalHealthAssessment(
                    scope="readiness",
                    status=RegionalHealthStatus.UNKNOWN,
                    reason_code=(
                        HealthReasonCode.CONFIGURATION_INVALID
                    ),
                    summary="configuration could not be loaded",
                    evaluated_at=evaluated_at,
                ).as_dict(),
                "observations": [
                    observation.as_dict(
                        evaluated_at=evaluated_at,
                    )
                    for observation in observations
                ],
                "checks": {
                    "configuration": {"status": "fail"},
                },
            },
        )

    evaluated_at = datetime.now(timezone.utc)

    try:
        dynamodb = boto3.client(
            "dynamodb",
            config=READINESS_CLIENT_CONFIG,
        )
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
        sqs = boto3.client(
            "sqs",
            config=READINESS_CLIENT_CONFIG,
        )
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
    regional_health = _regional_health(
        config=config,
        checks=checks,
        evaluated_at=evaluated_at,
    )
    observations = observations_from_checks(
        checks=checks,
        observed_at=evaluated_at,
        region=config.aws_region,
        deployment_id=config.deployment_id,
    )

    return build_response(
        200 if is_ready else 503,
        {
            "status": "ready" if is_ready else "not-ready",
            "check": "readiness",
            **_metadata(config),
            "regionalHealth": regional_health.as_dict(),
            "observations": [
                observation.as_dict(
                    evaluated_at=evaluated_at,
                )
                for observation in observations
            ],
            "checks": checks,
        },
    )
