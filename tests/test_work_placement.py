from __future__ import annotations

from core.region_routing import (
    RegionRoutingService,
    RegionTopology,
    RoutingAction,
)
from core.work_placement import (
    OwnershipCandidate,
    OwnershipSource,
    OwnershipStatus,
    RegionOwnership,
    WorkOwnershipResolver,
    WorkPlacementService,
)


def routing_service(
    current_region: str = "us-east-1",
) -> RegionRoutingService:
    return RegionRoutingService(
        RegionTopology(
            current_region=current_region,
            primary_region="us-east-1",
            secondary_regions=("us-west-2",),
            site_name="east" if current_region == "us-east-1" else "west",
            region_role="active",
        )
    )


def resolver(
    current_region: str = "us-east-1",
) -> WorkOwnershipResolver:
    service = routing_service(current_region)

    return WorkOwnershipResolver(
        service.topology
    )


def test_region_ownership_rejects_blank_owner_region():
    try:
        RegionOwnership(
            owner_region=" ",
            source=OwnershipSource.EXPLICIT,
        )
    except ValueError as error:
        assert "owner_region" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_resolves_explicit_configured_owner_region():
    resolution = resolver().resolve(
        OwnershipCandidate(
            owner_region="us-west-2",
            source=OwnershipSource.PERSISTED,
            reason="loaded from record",
        )
    )

    assert resolution.status == OwnershipStatus.RESOLVED
    assert resolution.owner_region == "us-west-2"
    assert resolution.source == OwnershipSource.PERSISTED
    assert resolution.ownership is not None
    assert resolution.ownership.as_dict() == {
        "ownerRegion": "us-west-2",
        "ownershipSource": "persisted",
        "ownershipReason": "loaded from record",
    }


def test_missing_owner_defaults_to_current_region_for_local_work():
    resolution = resolver("us-west-2").resolve(
        OwnershipCandidate(
            owner_region=None,
            default_source=OwnershipSource.LEGACY_UNSPECIFIED,
            reason="legacy record did not contain ownerRegion",
        )
    )

    assert resolution.status == OwnershipStatus.RESOLVED
    assert resolution.owner_region == "us-west-2"
    assert resolution.source == OwnershipSource.LEGACY_UNSPECIFIED


def test_blank_explicit_owner_is_unresolved_when_default_disabled():
    resolution = resolver().resolve(
        OwnershipCandidate(
            owner_region=" ",
            source=OwnershipSource.EXPLICIT,
            allow_default_local=False,
        )
    )

    assert resolution.status == OwnershipStatus.UNRESOLVED
    assert resolution.owner_region is None
    assert resolution.source == OwnershipSource.EXPLICIT


def test_unsupported_owner_region_is_invalid():
    resolution = resolver().resolve(
        OwnershipCandidate(
            owner_region="eu-central-1",
            source=OwnershipSource.MESSAGE_METADATA,
        )
    )

    assert resolution.status == OwnershipStatus.INVALID
    assert resolution.owner_region == "eu-central-1"
    assert resolution.source == OwnershipSource.MESSAGE_METADATA


def test_retry_candidate_preserves_persisted_owner_region():
    resolution = resolver("us-east-1").resolve(
        OwnershipCandidate(
            owner_region="us-west-2",
            source=OwnershipSource.PERSISTED,
            reason="idempotency retry uses stored ownerRegion",
        )
    )

    assert resolution.status == OwnershipStatus.RESOLVED
    assert resolution.owner_region == "us-west-2"
    assert resolution.source == OwnershipSource.PERSISTED


def test_placement_is_local_when_owner_matches_current_region():
    service = routing_service("us-east-1")
    placement = WorkPlacementService(
        ownership_resolver=WorkOwnershipResolver(service.topology),
        routing_service=service,
    ).evaluate(
        OwnershipCandidate(
            owner_region="us-east-1",
            source=OwnershipSource.EXPLICIT,
        )
    )

    assert placement.execute_locally
    assert placement.routing_decision is not None
    assert (
        placement.routing_decision.action
        == RoutingAction.EXECUTE_LOCAL
    )


def test_placement_is_non_local_for_configured_peer_owner():
    service = routing_service("us-east-1")
    placement = WorkPlacementService(
        ownership_resolver=WorkOwnershipResolver(service.topology),
        routing_service=service,
    ).evaluate(
        OwnershipCandidate(
            owner_region="us-west-2",
            source=OwnershipSource.MESSAGE_METADATA,
        )
    )

    assert not placement.execute_locally
    assert placement.routing_decision is not None
    assert (
        placement.routing_decision.action
        == RoutingAction.NON_LOCAL_REGION
    )
    assert placement.as_dict()["placementTargetRegion"] == "us-west-2"
    assert placement.routing_decision.placement_region == "us-west-2"
    assert placement.routing_decision.target_region == "us-west-2"


def test_placement_returns_invalid_without_routing_decision():
    service = routing_service("us-east-1")
    placement = WorkPlacementService(
        ownership_resolver=WorkOwnershipResolver(service.topology),
        routing_service=service,
    ).evaluate(
        OwnershipCandidate(
            owner_region="eu-central-1",
            source=OwnershipSource.EXPLICIT,
        )
    )

    assert not placement.execute_locally
    assert placement.routing_decision is None
    assert placement.ownership.status == OwnershipStatus.INVALID
    assert placement.as_dict()["placementAction"] == "INVALID"


def test_placement_returns_unresolved_without_transport_dependency():
    service = routing_service("us-east-1")
    placement = WorkPlacementService(
        ownership_resolver=WorkOwnershipResolver(service.topology),
        routing_service=service,
    ).evaluate(
        OwnershipCandidate(
            owner_region="",
            source=OwnershipSource.EXPLICIT,
            allow_default_local=False,
        )
    )

    assert placement.routing_decision is None
    assert placement.ownership.status == OwnershipStatus.UNRESOLVED
