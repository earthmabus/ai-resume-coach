from __future__ import annotations

import re
from pathlib import Path

from core.api_contract import (
    HANDLER_ONLY_ROUTES,
    LEGACY_OBSOLETE_ROUTES,
    PROTECTED_API_ROUTES,
    PUBLIC_API_ROUTES,
    handler_route_contract,
)
from lambdas.api.handler import build_routes


ROOT = Path(__file__).resolve().parents[1]
API_GATEWAY_TF = (
    ROOT / "infra/modules/regional_application/api_gateway.tf"
)


def _terraform_routes(local_name: str) -> set[str]:
    content = API_GATEWAY_TF.read_text()
    match = re.search(
        rf"{local_name}\s*=\s*toset\(\[(.*?)\]\)",
        content,
        re.DOTALL,
    )

    assert match is not None

    return set(re.findall(r'"([^"]+)"', match.group(1)))


def test_handler_routes_match_authoritative_contract():
    assert tuple(sorted(build_routes())) == handler_route_contract()


def test_gateway_protected_routes_match_handler_contract():
    assert _terraform_routes("protected_api_routes") == set(
        PROTECTED_API_ROUTES
    )


def test_gateway_public_routes_are_health_only():
    assert _terraform_routes("public_api_routes") == set(
        PUBLIC_API_ROUTES
    )
    assert "GET /version" in HANDLER_ONLY_ROUTES


def test_async_routes_cannot_silently_disappear():
    protected_routes = _terraform_routes("protected_api_routes")

    assert "POST /resume-upload-url" in protected_routes
    assert "POST /analyze-uploaded-resume" in protected_routes


def test_obsolete_gateway_routes_are_not_deployed():
    gateway_routes = (
        _terraform_routes("public_api_routes")
        | _terraform_routes("protected_api_routes")
    )

    for route in LEGACY_OBSOLETE_ROUTES:
        assert route not in gateway_routes
