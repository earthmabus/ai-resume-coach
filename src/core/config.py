from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


class ConfigurationError(RuntimeError):
    """Raised when required application configuration is unavailable."""


def _required(name: str) -> str:
    value = os.getenv(name)

    if value is None or not value.strip():
        raise ConfigurationError(
            f"Required environment variable {name} is not configured"
        )

    return value.strip()


def _optional_list(name: str) -> tuple[str, ...]:
    raw_value = os.getenv(name, "")

    return tuple(
        dict.fromkeys(
            value.strip()
            for value in raw_value.split(",")
            if value.strip()
        )
    )


@dataclass(frozen=True)
class AppConfig:
    project_name: str
    environment: str
    app_version: str
    deployment_id: str
    aws_region: str
    site_name: str
    region_role: str
    primary_region: str
    secondary_regions: tuple[str, ...]

    table_name: str
    document_bucket: str
    processing_queue_url: str

    analysis_provider: str
    openai_model: str
    log_level: str


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    aws_region = _required("AWS_REGION")

    return AppConfig(
        project_name=os.getenv("PROJECT_NAME", "ai-resume-coach"),
        environment=os.getenv("ENVIRONMENT", "dev"),
        app_version=os.getenv("APP_VERSION", "0.1.0"),
        deployment_id=os.getenv("DEPLOYMENT_ID", "local"),
        aws_region=aws_region,
        site_name=os.getenv("SITE_NAME", "local").strip() or "local",
        region_role=os.getenv("REGION_ROLE", "active").strip() or "active",
        primary_region=(
            os.getenv("PRIMARY_REGION", aws_region).strip()
            or aws_region
        ),
        secondary_regions=_optional_list("SECONDARY_REGIONS"),
        table_name=_required("RESUME_ANALYSIS_TABLE"),
        document_bucket=_required("DOCUMENT_BUCKET"),
        processing_queue_url=_required("RESUME_ANALYSIS_QUEUE_URL"),
        analysis_provider=os.getenv("ANALYSIS_PROVIDER", "rule-based"),
        openai_model=os.getenv("OPENAI_MODEL", ""),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )


def reset_config_cache() -> None:
    """Used by tests after environment variables are changed."""

    get_config.cache_clear()
