from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.config import get_config
from core.errors import (
    IdempotencyKeyRequiredError,
    ValidationError,
)


MIN_IDEMPOTENCY_KEY_LENGTH = 16
MAX_IDEMPOTENCY_KEY_LENGTH = 128


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    user_id: str
    region: str
    idempotency_key: str | None
    route_key: str
    method: str
    path: str


def get_header(event: dict[str, Any], name: str) -> str | None:
    """Return a request header using case-insensitive matching."""

    expected_name = name.lower()

    for key, value in (event.get("headers") or {}).items():
        if key.lower() == expected_name:
            normalized = str(value).strip() if value is not None else ""
            return normalized or None

    return None


def get_authenticated_user_id(event: dict[str, Any]) -> str:
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
    )

    user_id = claims.get("sub")

    if not user_id:
        raise ValidationError("Authenticated user identity is unavailable")

    return str(user_id)


def get_request_id(event: dict[str, Any]) -> str:
    request_id = event.get("requestContext", {}).get("requestId")

    if not request_id:
        raise ValidationError("Request identifier is unavailable")

    return str(request_id)


def get_route_key(event: dict[str, Any]) -> str:
    route_key = event.get("routeKey")

    if route_key:
        return str(route_key)

    request_context = event.get("requestContext", {})
    route_key = request_context.get("routeKey")

    if route_key:
        return str(route_key)

    http = request_context.get("http", {})
    method = str(http.get("method", "UNKNOWN"))
    path = str(http.get("path", "/"))

    return f"{method} {path}"


def require_idempotency_key(event: dict[str, Any]) -> str:
    key = get_header(event, "Idempotency-Key")

    if key is None:
        raise IdempotencyKeyRequiredError()

    if not (
        MIN_IDEMPOTENCY_KEY_LENGTH
        <= len(key)
        <= MAX_IDEMPOTENCY_KEY_LENGTH
    ):
        raise ValidationError(
            "Idempotency-Key must contain between "
            f"{MIN_IDEMPOTENCY_KEY_LENGTH} and "
            f"{MAX_IDEMPOTENCY_KEY_LENGTH} characters"
        )

    return key


def build_request_context(
    event: dict[str, Any],
    *,
    require_idempotency: bool = False,
) -> RequestContext:
    request_context = event.get("requestContext", {})
    http = request_context.get("http", {})

    idempotency_key = (
        require_idempotency_key(event)
        if require_idempotency
        else get_header(event, "Idempotency-Key")
    )

    return RequestContext(
        request_id=get_request_id(event),
        user_id=get_authenticated_user_id(event),
        region=get_config().aws_region,
        idempotency_key=idempotency_key,
        route_key=get_route_key(event),
        method=str(http.get("method", "UNKNOWN")),
        path=str(http.get("path", "/")),
    )
