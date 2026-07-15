from __future__ import annotations

import pytest

from core.errors import (
    IdempotencyKeyRequiredError,
    ValidationError,
)
from core.request_context import (
    build_request_context,
    get_authenticated_user_id,
    get_header,
    get_request_id,
    get_route_key,
    require_idempotency_key,
)


def make_event(
    *,
    headers: dict[str, str] | None = None,
    user_id: str | None = "user-123",
    request_id: str | None = "request-123",
    route_key: str | None = "POST /analyze-uploaded-resume",
    method: str = "POST",
    path: str = "/analyze-uploaded-resume",
) -> dict:
    claims = {}

    if user_id is not None:
        claims["sub"] = user_id

    request_context: dict = {
        "http": {
            "method": method,
            "path": path,
        },
        "authorizer": {
            "jwt": {
                "claims": claims,
            }
        },
    }

    if request_id is not None:
        request_context["requestId"] = request_id

    if route_key is not None:
        request_context["routeKey"] = route_key

    return {
        "headers": headers or {},
        "routeKey": route_key,
        "requestContext": request_context,
    }


def test_get_header_matches_case_insensitively():
    event = make_event(
        headers={
            "idempotency-key": "example-key-0001",
        }
    )

    assert (
        get_header(event, "Idempotency-Key")
        == "example-key-0001"
    )


def test_get_header_strips_surrounding_whitespace():
    event = make_event(
        headers={
            "Idempotency-Key": "  example-key-0001  ",
        }
    )

    assert (
        get_header(event, "Idempotency-Key")
        == "example-key-0001"
    )


def test_get_header_returns_none_when_missing():
    event = make_event(headers={})

    assert get_header(event, "Idempotency-Key") is None


def test_get_header_returns_none_for_blank_value():
    event = make_event(
        headers={
            "Idempotency-Key": "   ",
        }
    )

    assert get_header(event, "Idempotency-Key") is None


def test_get_authenticated_user_id_returns_cognito_subject():
    event = make_event(user_id="user-456")

    assert get_authenticated_user_id(event) == "user-456"


def test_get_authenticated_user_id_raises_when_claim_missing():
    event = make_event(user_id=None)

    with pytest.raises(
        ValidationError,
        match="Authenticated user identity is unavailable",
    ):
        get_authenticated_user_id(event)


def test_get_request_id_returns_api_gateway_request_id():
    event = make_event(request_id="request-456")

    assert get_request_id(event) == "request-456"


def test_get_request_id_raises_when_missing():
    event = make_event(request_id=None)

    with pytest.raises(
        ValidationError,
        match="Request identifier is unavailable",
    ):
        get_request_id(event)


def test_get_route_key_prefers_top_level_route_key():
    event = make_event(
        route_key="POST /analyze-uploaded-resume",
    )

    event["requestContext"]["routeKey"] = "POST /different-route"

    assert (
        get_route_key(event)
        == "POST /analyze-uploaded-resume"
    )


def test_get_route_key_uses_request_context_route_key():
    event = make_event(
        route_key="POST /analyze-uploaded-resume",
    )

    event.pop("routeKey")

    assert (
        get_route_key(event)
        == "POST /analyze-uploaded-resume"
    )


def test_get_route_key_falls_back_to_method_and_path():
    event = make_event(
        route_key=None,
        method="PUT",
        path="/profile",
    )

    assert get_route_key(event) == "PUT /profile"


def test_require_idempotency_key_returns_valid_key():
    event = make_event(
        headers={
            "Idempotency-Key": "12345678-1234-1234-1234-123456789012",
        }
    )

    assert require_idempotency_key(event) == (
        "12345678-1234-1234-1234-123456789012"
    )


def test_require_idempotency_key_raises_when_missing():
    event = make_event(headers={})

    with pytest.raises(IdempotencyKeyRequiredError):
        require_idempotency_key(event)


def test_require_idempotency_key_rejects_short_key():
    event = make_event(
        headers={
            "Idempotency-Key": "too-short",
        }
    )

    with pytest.raises(
        ValidationError,
        match="between 16 and 128 characters",
    ):
        require_idempotency_key(event)


def test_require_idempotency_key_rejects_long_key():
    event = make_event(
        headers={
            "Idempotency-Key": "x" * 129,
        }
    )

    with pytest.raises(
        ValidationError,
        match="between 16 and 128 characters",
    ):
        require_idempotency_key(event)


def test_build_request_context_includes_expected_values():
    event = make_event(
        headers={
            "IDEMPOTENCY-KEY": (
                "12345678-1234-1234-1234-123456789012"
            ),
        },
        user_id="user-789",
        request_id="request-789",
    )

    context = build_request_context(
        event,
        require_idempotency=True,
    )

    assert context.user_id == "user-789"
    assert context.request_id == "request-789"
    assert context.region == "us-east-1"
    assert context.route_key == (
        "POST /analyze-uploaded-resume"
    )
    assert context.method == "POST"
    assert context.path == "/analyze-uploaded-resume"
    assert context.idempotency_key == (
        "12345678-1234-1234-1234-123456789012"
    )


def test_build_request_context_allows_optional_missing_key():
    event = make_event(headers={})

    context = build_request_context(
        event,
        require_idempotency=False,
    )

    assert context.idempotency_key is None
