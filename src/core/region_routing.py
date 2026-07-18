from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.config import AppConfig, get_config


class RoutingAction(str, Enum):
    EXECUTE_LOCAL = "EXECUTE_LOCAL"
    NON_LOCAL_REGION = "NON_LOCAL_REGION"
    REJECT = "REJECT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RegionTopology:
    current_region: str
    primary_region: str
    secondary_regions: tuple[str, ...]
    site_name: str
    region_role: str

    @property
    def configured_regions(self) -> tuple[str, ...]:
        regions = (
            self.primary_region,
            self.current_region,
            *self.secondary_regions,
        )

        return tuple(
            dict.fromkeys(
                region
                for region in regions
                if region
            )
        )

    def contains_region(self, region: str) -> bool:
        return region in self.configured_regions


@dataclass(frozen=True)
class RoutingRequest:
    owner_region: str | None = None
    operation: str | None = None


@dataclass(frozen=True)
class RoutingDecision:
    action: RoutingAction
    current_region: str
    owner_region: str | None = None
    target_region: str | None = None
    reason: str = ""

    @property
    def execute_locally(self) -> bool:
        return self.action == RoutingAction.EXECUTE_LOCAL

    @classmethod
    def execute_local(
        cls,
        *,
        current_region: str,
        owner_region: str | None = None,
        reason: str = "local execution selected",
    ) -> "RoutingDecision":
        return cls(
            action=RoutingAction.EXECUTE_LOCAL,
            current_region=current_region,
            owner_region=owner_region,
            target_region=current_region,
            reason=reason,
        )

    @classmethod
    def non_local_region(
        cls,
        *,
        current_region: str,
        owner_region: str,
        target_region: str,
        reason: str = "request owner is another configured region",
    ) -> "RoutingDecision":
        return cls(
            action=RoutingAction.NON_LOCAL_REGION,
            current_region=current_region,
            owner_region=owner_region,
            target_region=target_region,
            reason=reason,
        )

    @classmethod
    def reject(
        cls,
        *,
        current_region: str,
        owner_region: str | None,
        reason: str,
    ) -> "RoutingDecision":
        return cls(
            action=RoutingAction.REJECT,
            current_region=current_region,
            owner_region=owner_region,
            reason=reason,
        )

    @classmethod
    def unknown(
        cls,
        *,
        current_region: str,
        owner_region: str | None,
        reason: str,
    ) -> "RoutingDecision":
        return cls(
            action=RoutingAction.UNKNOWN,
            current_region=current_region,
            owner_region=owner_region,
            reason=reason,
        )


def topology_from_config(config: AppConfig | None = None) -> RegionTopology:
    resolved = config or get_config()

    return RegionTopology(
        current_region=resolved.aws_region,
        primary_region=resolved.primary_region,
        secondary_regions=resolved.secondary_regions,
        site_name=resolved.site_name,
        region_role=resolved.region_role,
    )


class RegionRoutingService:
    def __init__(self, topology: RegionTopology | None = None) -> None:
        self._topology = topology or topology_from_config()

    @property
    def topology(self) -> RegionTopology:
        return self._topology

    def decide(
        self,
        request: RoutingRequest | None = None,
    ) -> RoutingDecision:
        routing_request = request or RoutingRequest()
        owner_region = (
            routing_request.owner_region.strip()
            if routing_request.owner_region
            else None
        )

        if owner_region is None:
            return RoutingDecision.execute_local(
                current_region=self._topology.current_region,
                reason="no owner region was supplied",
            )

        if owner_region == self._topology.current_region:
            return RoutingDecision.execute_local(
                current_region=self._topology.current_region,
                owner_region=owner_region,
                reason="owner region matches current region",
            )

        if self._topology.contains_region(owner_region):
            return RoutingDecision.non_local_region(
                current_region=self._topology.current_region,
                owner_region=owner_region,
                target_region=owner_region,
            )

        return RoutingDecision.reject(
            current_region=self._topology.current_region,
            owner_region=owner_region,
            reason="owner region is not configured",
        )


def current_region_routing_service() -> RegionRoutingService:
    return RegionRoutingService()
