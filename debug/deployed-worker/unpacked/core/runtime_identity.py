from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.config import get_config


@dataclass(frozen=True)
class RuntimeIdentity:
    project_name: str
    environment: str
    app_version: str
    deployment_id: str
    region: str

    @property
    def short_deployment_id(self) -> str:
        return self.deployment_id[:12]

    def as_dict(self) -> dict[str, str]:
        return {
            "project": self.project_name,
            "environment": self.environment,
            "version": self.app_version,
            "deploymentId": self.deployment_id,
            "region": self.region,
        }

    def creation_metadata(self) -> dict[str, str]:
        return {
            "createdRegion": self.region,
            "createdByDeploymentId": self.deployment_id,
            "lastUpdatedRegion": self.region,
            "lastUpdatedByDeploymentId": self.deployment_id,
        }

    def update_metadata(self) -> dict[str, str]:
        return {
            "lastUpdatedRegion": self.region,
            "lastUpdatedByDeploymentId": self.deployment_id,
        }

    def processing_metadata(self) -> dict[str, str]:
        return {
            "processedRegion": self.region,
            "processedByDeploymentId": self.deployment_id,
        }


def current_runtime_identity() -> RuntimeIdentity:
    config = get_config()

    return RuntimeIdentity(
        project_name=config.project_name,
        environment=config.environment,
        app_version=config.app_version,
        deployment_id=config.deployment_id,
        region=config.aws_region,
    )


def enrich_response_body(
    body: Any,
    *,
    identity: RuntimeIdentity | None = None,
) -> Any:
    """
    Add a stable runtime envelope to dictionary responses.

    Existing response fields remain unchanged. Non-dictionary bodies are
    returned unchanged.
    """
    if not isinstance(body, dict):
        return body

    runtime = identity or current_runtime_identity()

    return {
        **body,
        "runtime": runtime.as_dict(),
    }
