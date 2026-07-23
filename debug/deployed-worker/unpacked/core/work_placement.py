from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.region_routing import (
    RegionTopology,
    RegionRoutingService,
    RoutingDecision,
    RoutingRequest,
    normalize_region,
)


class OwnershipSource(str, Enum):
    EXPLICIT = "explicit"
    PERSISTED = "persisted"
    MESSAGE_METADATA = "message_metadata"
    CREATED_REGION = "created_region"
    DEFAULT_LOCAL = "default_local"
    LEGACY_UNSPECIFIED = "legacy_unspecified"


class OwnershipStatus(str, Enum):
    RESOLVED = "RESOLVED"
    INVALID = "INVALID"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class RegionOwnership:
    owner_region: str
    source: OwnershipSource
    reason: str = ""

    def __post_init__(self) -> None:
        owner_region = normalize_region(self.owner_region)

        if not owner_region:
            raise ValueError("owner_region must not be blank")

        object.__setattr__(
            self,
            "owner_region",
            owner_region,
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "ownerRegion": self.owner_region,
            "ownershipSource": self.source.value,
            "ownershipReason": self.reason,
        }


@dataclass(frozen=True)
class OwnershipCandidate:
    owner_region: str | None = None
    source: OwnershipSource = OwnershipSource.EXPLICIT
    reason: str = ""
    allow_default_local: bool = True
    default_source: OwnershipSource = OwnershipSource.DEFAULT_LOCAL


@dataclass(frozen=True)
class OwnershipResolution:
    status: OwnershipStatus
    ownership: RegionOwnership | None = None
    owner_region: str | None = None
    source: OwnershipSource | None = None
    reason: str = ""

    @property
    def resolved(self) -> bool:
        return self.status == OwnershipStatus.RESOLVED

    @classmethod
    def resolved_ownership(
        cls,
        ownership: RegionOwnership,
    ) -> "OwnershipResolution":
        return cls(
            status=OwnershipStatus.RESOLVED,
            ownership=ownership,
            owner_region=ownership.owner_region,
            source=ownership.source,
            reason=ownership.reason,
        )

    @classmethod
    def invalid(
        cls,
        *,
        owner_region: str | None,
        source: OwnershipSource | None,
        reason: str,
    ) -> "OwnershipResolution":
        return cls(
            status=OwnershipStatus.INVALID,
            owner_region=owner_region,
            source=source,
            reason=reason,
        )

    @classmethod
    def unresolved(
        cls,
        *,
        source: OwnershipSource | None,
        reason: str,
    ) -> "OwnershipResolution":
        return cls(
            status=OwnershipStatus.UNRESOLVED,
            source=source,
            reason=reason,
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "ownershipStatus": self.status.value,
            "ownerRegion": self.owner_region or "",
            "ownershipSource": (
                self.source.value
                if self.source is not None
                else ""
            ),
            "ownershipReason": self.reason,
        }


class WorkOwnershipResolver:
    def __init__(self, topology: RegionTopology) -> None:
        self._topology = topology

    def resolve(
        self,
        candidate: OwnershipCandidate | None = None,
    ) -> OwnershipResolution:
        resolved_candidate = candidate or OwnershipCandidate()
        owner_region = normalize_region(
            resolved_candidate.owner_region
        )

        if not owner_region:
            if not resolved_candidate.allow_default_local:
                return OwnershipResolution.unresolved(
                    source=resolved_candidate.source,
                    reason="owner region was not supplied",
                )

            return OwnershipResolution.resolved_ownership(
                RegionOwnership(
                    owner_region=(
                        self._topology.current_region
                    ),
                    source=resolved_candidate.default_source,
                    reason=(
                        resolved_candidate.reason
                        or "defaulted to current region"
                    ),
                )
            )

        if not self._topology.contains_region(
            owner_region
        ):
            return OwnershipResolution.invalid(
                owner_region=owner_region,
                source=resolved_candidate.source,
                reason="owner region is not configured",
            )

        return OwnershipResolution.resolved_ownership(
            RegionOwnership(
                owner_region=owner_region,
                source=resolved_candidate.source,
                reason=(
                    resolved_candidate.reason
                    or "explicit owner region supplied"
                ),
            )
        )


@dataclass(frozen=True)
class WorkPlacementResult:
    ownership: OwnershipResolution
    routing_decision: RoutingDecision | None = None

    @property
    def action(self) -> str:
        if self.routing_decision is None:
            return self.ownership.status.value

        return self.routing_decision.action.value

    @property
    def execute_locally(self) -> bool:
        return (
            self.routing_decision.execute_locally
            if self.routing_decision is not None
            else False
        )

    def as_dict(self) -> dict[str, str]:
        diagnostic = self.ownership.as_dict()

        if self.routing_decision is None:
            diagnostic.update(
                {
                    "placementAction": self.ownership.status.value,
                    "placementReason": self.ownership.reason,
                    "currentRegion": "",
                    "placementTargetRegion": "",
                }
            )
            return diagnostic

        diagnostic.update(
            {
                "placementAction": (
                    self.routing_decision.action.value
                ),
                "placementReason": self.routing_decision.reason,
                "currentRegion": (
                    self.routing_decision.current_region
                ),
                "placementTargetRegion": (
                    self.routing_decision.placement_region or ""
                ),
            }
        )

        return diagnostic


class WorkPlacementService:
    def __init__(
        self,
        *,
        ownership_resolver: WorkOwnershipResolver,
        routing_service: RegionRoutingService,
    ) -> None:
        self._ownership_resolver = ownership_resolver
        self._routing_service = routing_service

    def evaluate(
        self,
        candidate: OwnershipCandidate | None = None,
    ) -> WorkPlacementResult:
        ownership = self._ownership_resolver.resolve(candidate)

        if not ownership.resolved:
            return WorkPlacementResult(
                ownership=ownership,
                routing_decision=None,
            )

        routing_decision = self._routing_service.decide(
            RoutingRequest(
                owner_region=ownership.owner_region,
            )
        )

        return WorkPlacementResult(
            ownership=ownership,
            routing_decision=routing_decision,
        )


def current_work_placement_service() -> WorkPlacementService:
    routing_service = RegionRoutingService()

    return WorkPlacementService(
        ownership_resolver=WorkOwnershipResolver(
            routing_service.topology
        ),
        routing_service=routing_service,
    )
