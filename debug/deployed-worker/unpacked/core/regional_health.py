from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, Mapping


DEFAULT_OBSERVATION_FRESHNESS_SECONDS = 60


class RegionalHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class HealthCheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class HealthDimension(str, Enum):
    PROCESSING = "processing"
    PERSISTENCE = "persistence"
    CONFIGURATION = "configuration"


class HealthReasonCode(str, Enum):
    ALL_REQUIRED_CHECKS_PASS = "ALL_REQUIRED_CHECKS_PASS"
    CONFIGURATION_INVALID = "CONFIGURATION_INVALID"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    PARTIAL_DEPENDENCY_FAILURE = "PARTIAL_DEPENDENCY_FAILURE"
    OBSERVATION_STALE = "OBSERVATION_STALE"
    OBSERVATION_MISSING = "OBSERVATION_MISSING"
    OBSERVATION_UNRECOGNIZED = "OBSERVATION_UNRECOGNIZED"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    normalized = value
    if normalized.tzinfo is None:
        normalized = normalized.replace(tzinfo=timezone.utc)

    return normalized.astimezone(timezone.utc)


def isoformat_utc(value: datetime) -> str:
    return as_utc(value).isoformat()


@dataclass(frozen=True)
class HealthObservation:
    dimension: HealthDimension
    name: str
    status: HealthCheckStatus
    observed_at: datetime
    freshness_seconds: int = DEFAULT_OBSERVATION_FRESHNESS_SECONDS
    reason_code: HealthReasonCode = (
        HealthReasonCode.ALL_REQUIRED_CHECKS_PASS
    )
    region: str = ""
    deployment_id: str = ""

    def __post_init__(self) -> None:
        name = str(self.name or "").strip()
        if not name:
            raise ValueError("name must not be blank")

        freshness_seconds = int(self.freshness_seconds)
        if freshness_seconds <= 0:
            raise ValueError(
                "freshness_seconds must be greater than zero"
            )

        object.__setattr__(
            self,
            "name",
            name,
        )
        object.__setattr__(
            self,
            "freshness_seconds",
            freshness_seconds,
        )
        object.__setattr__(
            self,
            "region",
            str(self.region or "").strip(),
        )
        object.__setattr__(
            self,
            "deployment_id",
            str(self.deployment_id or "").strip(),
        )

    def is_fresh(
        self,
        *,
        evaluated_at: datetime,
    ) -> bool:
        age_seconds = (
            as_utc(evaluated_at)
            - as_utc(self.observed_at)
        ).total_seconds()

        return 0 <= age_seconds <= self.freshness_seconds

    def as_dict(
        self,
        *,
        evaluated_at: datetime | None = None,
    ) -> dict[str, object]:
        evaluated = evaluated_at or utc_now()

        return {
            "dimension": self.dimension.value,
            "name": self.name,
            "status": self.status.value,
            "observedAt": isoformat_utc(self.observed_at),
            "freshnessSeconds": self.freshness_seconds,
            "fresh": self.is_fresh(evaluated_at=evaluated),
            "reasonCode": self.reason_code.value,
            "region": self.region,
            "deploymentId": self.deployment_id,
        }


@dataclass(frozen=True)
class RegionalHealthAssessment:
    scope: str
    status: RegionalHealthStatus
    reason_code: HealthReasonCode
    summary: str
    current_region: str = ""
    site_name: str = ""
    region_role: str = ""
    environment: str = ""
    deployment_id: str = ""
    evaluated_at: datetime | None = None

    def __post_init__(self) -> None:
        scope = str(self.scope or "").strip()
        if not scope:
            raise ValueError("scope must not be blank")

        object.__setattr__(self, "scope", scope)

    def as_dict(self) -> dict[str, str]:
        return {
            "scope": self.scope,
            "status": self.status.value,
            "reasonCode": self.reason_code.value,
            "summary": self.summary,
            "currentRegion": self.current_region,
            "siteName": self.site_name,
            "regionRole": self.region_role,
            "environment": self.environment,
            "deploymentId": self.deployment_id,
            "evaluatedAt": (
                isoformat_utc(self.evaluated_at)
                if self.evaluated_at is not None
                else ""
            ),
        }


def observation_from_check(
    *,
    name: str,
    check: Mapping[str, object],
    observed_at: datetime,
    region: str = "",
    deployment_id: str = "",
) -> HealthObservation:
    status_value = str(
        check.get("status") or ""
    ).strip().lower()
    allowed_statuses = {
        item.value
        for item in HealthCheckStatus
    }
    status = (
        HealthCheckStatus(status_value)
        if status_value in allowed_statuses
        else HealthCheckStatus.UNKNOWN
    )

    if name == "configuration":
        dimension = HealthDimension.CONFIGURATION
    elif name == "dynamodb":
        dimension = HealthDimension.PERSISTENCE
    elif name == "sqs":
        dimension = HealthDimension.PROCESSING
    else:
        raise ValueError(f"unsupported health check: {name}")

    if status == HealthCheckStatus.PASS:
        reason_code = HealthReasonCode.ALL_REQUIRED_CHECKS_PASS
    elif name == "configuration":
        reason_code = HealthReasonCode.CONFIGURATION_INVALID
    elif status == HealthCheckStatus.FAIL:
        reason_code = HealthReasonCode.DEPENDENCY_UNAVAILABLE
    else:
        reason_code = HealthReasonCode.OBSERVATION_UNRECOGNIZED

    return HealthObservation(
        dimension=dimension,
        name=name,
        status=status,
        observed_at=observed_at,
        reason_code=reason_code,
        region=region,
        deployment_id=deployment_id,
    )


def observations_from_checks(
    *,
    checks: Mapping[str, Mapping[str, object]],
    observed_at: datetime,
    region: str = "",
    deployment_id: str = "",
) -> tuple[HealthObservation, ...]:
    return tuple(
        observation_from_check(
            name=name,
            check=check,
            observed_at=observed_at,
            region=region,
            deployment_id=deployment_id,
        )
        for name, check in checks.items()
    )


def classify_observations(
    *,
    observations: Iterable[HealthObservation],
    evaluated_at: datetime | None = None,
    current_region: str = "",
    site_name: str = "",
    region_role: str = "",
    environment: str = "",
    deployment_id: str = "",
) -> RegionalHealthAssessment:
    evaluated = evaluated_at or utc_now()
    observed = tuple(observations)

    if not observed:
        return RegionalHealthAssessment(
            scope="readiness",
            status=RegionalHealthStatus.UNKNOWN,
            reason_code=HealthReasonCode.OBSERVATION_MISSING,
            summary="no health observations were available",
            current_region=current_region,
            site_name=site_name,
            region_role=region_role,
            environment=environment,
            deployment_id=deployment_id,
            evaluated_at=evaluated,
        )

    if any(
        not observation.is_fresh(evaluated_at=evaluated)
        for observation in observed
    ):
        return RegionalHealthAssessment(
            scope="readiness",
            status=RegionalHealthStatus.UNKNOWN,
            reason_code=HealthReasonCode.OBSERVATION_STALE,
            summary="one or more health observations are stale",
            current_region=current_region,
            site_name=site_name,
            region_role=region_role,
            environment=environment,
            deployment_id=deployment_id,
            evaluated_at=evaluated,
        )

    if any(
        observation.status == HealthCheckStatus.UNKNOWN
        for observation in observed
    ):
        return RegionalHealthAssessment(
            scope="readiness",
            status=RegionalHealthStatus.UNKNOWN,
            reason_code=HealthReasonCode.OBSERVATION_UNRECOGNIZED,
            summary="one or more health observations are unknown",
            current_region=current_region,
            site_name=site_name,
            region_role=region_role,
            environment=environment,
            deployment_id=deployment_id,
            evaluated_at=evaluated,
        )

    runtime_observations = tuple(
        observation
        for observation in observed
        if observation.dimension != HealthDimension.CONFIGURATION
    )

    if not runtime_observations and any(
        observation.dimension == HealthDimension.CONFIGURATION
        and observation.status == HealthCheckStatus.FAIL
        for observation in observed
    ):
        return RegionalHealthAssessment(
            scope="readiness",
            status=RegionalHealthStatus.UNKNOWN,
            reason_code=HealthReasonCode.CONFIGURATION_INVALID,
            summary="configuration observations are invalid",
            current_region=current_region,
            site_name=site_name,
            region_role=region_role,
            environment=environment,
            deployment_id=deployment_id,
            evaluated_at=evaluated,
        )

    classified = runtime_observations or observed
    statuses = {
        observation.status
        for observation in classified
    }

    if statuses == {HealthCheckStatus.PASS}:
        status = RegionalHealthStatus.HEALTHY
        reason_code = HealthReasonCode.ALL_REQUIRED_CHECKS_PASS
        summary = "all required observations passed"
    elif statuses == {HealthCheckStatus.FAIL}:
        status = RegionalHealthStatus.UNAVAILABLE
        reason_code = HealthReasonCode.DEPENDENCY_UNAVAILABLE
        summary = "all observed readiness dependencies failed"
    elif (
        HealthCheckStatus.PASS in statuses
        and HealthCheckStatus.FAIL in statuses
    ):
        status = RegionalHealthStatus.DEGRADED
        reason_code = HealthReasonCode.PARTIAL_DEPENDENCY_FAILURE
        summary = "one or more runtime capabilities are impaired"
    else:
        status = RegionalHealthStatus.UNKNOWN
        reason_code = HealthReasonCode.OBSERVATION_UNRECOGNIZED
        summary = "health observations are unrecognized"

    return RegionalHealthAssessment(
        scope="readiness",
        status=status,
        reason_code=reason_code,
        summary=summary,
        current_region=current_region,
        site_name=site_name,
        region_role=region_role,
        environment=environment,
        deployment_id=deployment_id,
        evaluated_at=evaluated,
    )


def classify_readiness_health(
    *,
    checks: Mapping[str, Mapping[str, object]],
    current_region: str = "",
    site_name: str = "",
    region_role: str = "",
    environment: str = "",
    deployment_id: str = "",
    evaluated_at: datetime | None = None,
) -> RegionalHealthAssessment:
    evaluated = evaluated_at or utc_now()

    return classify_observations(
        observations=observations_from_checks(
            checks=checks,
            observed_at=evaluated,
            region=current_region,
            deployment_id=deployment_id,
        ),
        evaluated_at=evaluated,
        current_region=current_region,
        site_name=site_name,
        region_role=region_role,
        environment=environment,
        deployment_id=deployment_id,
    )


def classify_regional_health(
    *,
    checks: Mapping[str, Mapping[str, object]],
    current_region: str = "",
    site_name: str = "",
    region_role: str = "",
    environment: str = "",
    deployment_id: str = "",
    evaluated_at: datetime | None = None,
) -> RegionalHealthAssessment:
    return classify_readiness_health(
        checks=checks,
        current_region=current_region,
        site_name=site_name,
        region_role=region_role,
        environment=environment,
        deployment_id=deployment_id,
        evaluated_at=evaluated_at,
    )
