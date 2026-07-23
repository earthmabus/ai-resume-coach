from __future__ import annotations

import json
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


def _optional_json_string_map(name: str) -> dict[str, str]:
    raw_value = str(
        os.getenv(name, "{}") or "{}"
    ).strip()

    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise ConfigurationError(
            f"{name} must be a JSON object"
        ) from error

    if not isinstance(parsed, dict):
        raise ConfigurationError(
            f"{name} must be a JSON object"
        )

    return {
        str(key or "").strip(): str(value or "").strip()
        for key, value in parsed.items()
        if str(key or "").strip()
        and str(value or "").strip()
    }


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
    witness_region: str

    table_name: str
    document_bucket: str
    processing_queue_url: str
    regional_processing_queue_names: dict[str, str]

    analysis_provider: str
    openai_model: str
    log_level: str
    enable_synthetic_placement_override: bool
    synthetic_placement_override_group: str


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
        witness_region=os.getenv("WITNESS_REGION", "").strip(),
        table_name=_required("RESUME_ANALYSIS_TABLE"),
        document_bucket=_required("DOCUMENT_BUCKET"),
        processing_queue_url=_required("RESUME_ANALYSIS_QUEUE_URL"),
        regional_processing_queue_names=_optional_json_string_map(
            "REGIONAL_PROCESSING_QUEUE_NAMES"
        ),
        analysis_provider=os.getenv("ANALYSIS_PROVIDER", "rule-based"),
        openai_model=os.getenv("OPENAI_MODEL", ""),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        enable_synthetic_placement_override=(
            os.getenv(
                "ENABLE_SYNTHETIC_PLACEMENT_OVERRIDE",
                "false",
            )
            .strip()
            .lower()
            == "true"
        ),
        synthetic_placement_override_group=(
            os.getenv(
                "SYNTHETIC_PLACEMENT_OVERRIDE_GROUP",
                "",
            ).strip()
        ),
    )


def reset_config_cache() -> None:
    """Used by tests after environment variables are changed."""

    get_config.cache_clear()
