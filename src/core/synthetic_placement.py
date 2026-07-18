from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.config import AppConfig, get_config
from core.errors import ForbiddenError, ValidationError
from core.region_routing import normalize_region, topology_from_config
from core.request_context import get_header
from core.work_placement import (
    OwnershipCandidate,
    OwnershipSource,
    WorkOwnershipResolver,
)


VALIDATION_OWNER_REGION_HEADER = "X-Validation-Owner-Region"


@dataclass(frozen=True)
class SyntheticPlacementOverride:
    owner_region: str
    used: bool = False


def _claims(event: dict[str, Any]) -> dict[str, Any]:
    raw_claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
    )

    return raw_claims if isinstance(raw_claims, dict) else {}


def _has_header(event: dict[str, Any], name: str) -> bool:
    expected_name = name.lower()

    for key in (event.get("headers") or {}):
        if key.lower() == expected_name:
            return True

    return False


def _claim_values(value: Any) -> set[str]:
    if value is None:
        return set()

    if isinstance(value, (list, tuple, set)):
        return {
            str(item).strip()
            for item in value
            if str(item).strip()
        }

    return {
        item.strip()
        for item in str(value).split(",")
        if item.strip()
    }


def _has_validation_group(
    event: dict[str, Any],
    *,
    group_name: str,
) -> bool:
    claims = _claims(event)
    group_values = set()

    for claim_name in ("cognito:groups", "groups"):
        group_values.update(_claim_values(claims.get(claim_name)))

    return group_name in group_values


def resolve_synthetic_owner_region(
    event: dict[str, Any],
    *,
    config: AppConfig | None = None,
) -> SyntheticPlacementOverride | None:
    requested_owner_region = get_header(
        event,
        VALIDATION_OWNER_REGION_HEADER,
    )

    if requested_owner_region is None:
        if _has_header(event, VALIDATION_OWNER_REGION_HEADER):
            raise ValidationError("Owner region must not be blank")

        return None

    resolved_config = config or get_config()

    if (
        resolved_config.environment != "dev"
        or not resolved_config.enable_synthetic_placement_override
    ):
        raise ForbiddenError(
            "Synthetic placement override is not enabled"
        )

    group_name = resolved_config.synthetic_placement_override_group

    if not group_name:
        raise ForbiddenError(
            "Synthetic placement override has no authorized group"
        )

    if not _has_validation_group(event, group_name=group_name):
        raise ForbiddenError(
            "Synthetic placement override is not authorized"
        )

    owner_region = normalize_region(requested_owner_region)

    if not owner_region:
        raise ValidationError("Owner region must not be blank")

    if (
        resolved_config.witness_region
        and owner_region == resolved_config.witness_region
    ):
        raise ValidationError(
            "Witness region cannot own application work"
        )

    resolver = WorkOwnershipResolver(
        topology_from_config(resolved_config)
    )
    ownership = resolver.resolve(
        OwnershipCandidate(
            owner_region=owner_region,
            source=OwnershipSource.EXPLICIT,
            reason="development synthetic placement override",
            allow_default_local=False,
        )
    )

    if not ownership.resolved or not ownership.owner_region:
        raise ValidationError(
            ownership.reason or "Owner region is not configured"
        )

    return SyntheticPlacementOverride(
        owner_region=ownership.owner_region,
        used=True,
    )
