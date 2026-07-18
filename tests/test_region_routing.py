from __future__ import annotations

from core.region_routing import (
    RegionRoutingService,
    RegionTopology,
    RoutingAction,
    RoutingDecision,
    RoutingRequest,
    topology_from_config,
)


def topology() -> RegionTopology:
    return RegionTopology(
        current_region="us-east-1",
        primary_region="us-east-1",
        secondary_regions=("us-west-2",),
        site_name="east",
        region_role="active",
    )


def test_topology_from_config_uses_centralized_configuration():
    resolved = topology_from_config()

    assert resolved.current_region == "us-east-1"
    assert resolved.primary_region == "us-east-1"
    assert resolved.secondary_regions == ("us-west-2",)
    assert resolved.site_name == "east"
    assert resolved.region_role == "active"
    assert resolved.configured_regions == (
        "us-east-1",
        "us-west-2",
    )


def test_default_routing_decision_executes_locally():
    decision = RegionRoutingService(topology()).decide()

    assert decision.action == RoutingAction.EXECUTE_LOCAL
    assert decision.execute_locally
    assert decision.current_region == "us-east-1"
    assert decision.target_region == "us-east-1"
    assert decision.owner_region is None


def test_request_owned_by_current_region_executes_locally():
    decision = RegionRoutingService(topology()).decide(
        RoutingRequest(owner_region="us-east-1")
    )

    assert decision.action == RoutingAction.EXECUTE_LOCAL
    assert decision.execute_locally
    assert decision.owner_region == "us-east-1"
    assert decision.target_region == "us-east-1"


def test_request_owned_by_configured_peer_returns_non_local_decision():
    decision = RegionRoutingService(topology()).decide(
        RoutingRequest(owner_region="us-west-2")
    )

    assert decision.action == RoutingAction.NON_LOCAL_REGION
    assert not decision.execute_locally
    assert decision.current_region == "us-east-1"
    assert decision.owner_region == "us-west-2"
    assert decision.target_region == "us-west-2"


def test_unknown_owner_region_is_rejected_without_forwarding():
    decision = RegionRoutingService(topology()).decide(
        RoutingRequest(owner_region="eu-central-1")
    )

    assert decision.action == RoutingAction.REJECT
    assert not decision.execute_locally
    assert decision.current_region == "us-east-1"
    assert decision.owner_region == "eu-central-1"
    assert decision.target_region is None


def test_topology_deduplicates_configured_regions_in_order():
    resolved = RegionTopology(
        current_region="us-west-2",
        primary_region="us-east-1",
        secondary_regions=(
            "us-west-2",
            "us-east-1",
        ),
        site_name="west",
        region_role="active",
    )

    assert resolved.configured_regions == (
        "us-east-1",
        "us-west-2",
    )


def test_unknown_decision_is_available_for_future_extensions():
    decision = RoutingDecision.unknown(
        current_region="us-east-1",
        owner_region=None,
        reason="request ownership cannot be determined",
    )

    assert decision.action == RoutingAction.UNKNOWN
    assert not decision.execute_locally
    assert decision.target_region is None
