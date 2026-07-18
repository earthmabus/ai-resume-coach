from __future__ import annotations

from core.request_context import (
    build_request_context,
    is_valid_correlation_id,
)


def test_request_context_includes_runtime_identity():
    event = {
        "routeKey": "GET /profile",
        "requestContext": {
            "requestId": "request-123",
            "http": {
                "method": "GET",
                "path": "/profile",
            },
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                    }
                }
            },
        },
    }

    context = build_request_context(event)

    assert context.region == "us-east-1"
    assert context.deployment_id == "test-deployment"
    assert context.environment == "test"
    assert context.request_id == "request-123"
    assert context.correlation_id == "request-123"


def test_request_context_uses_valid_correlation_header():
    event = {
        "headers": {
            "X-Correlation-Id": "corr-123456",
        },
        "routeKey": "GET /profile",
        "requestContext": {
            "requestId": "request-123",
            "http": {
                "method": "GET",
                "path": "/profile",
            },
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                    }
                }
            },
        },
    }

    context = build_request_context(event)

    assert context.request_id == "request-123"
    assert context.correlation_id == "corr-123456"


def test_invalid_correlation_header_falls_back_to_request_id():
    event = {
        "headers": {
            "x-correlation-id": "bad value with spaces",
        },
        "routeKey": "GET /profile",
        "requestContext": {
            "requestId": "request-123",
            "http": {
                "method": "GET",
                "path": "/profile",
            },
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                    }
                }
            },
        },
    }

    context = build_request_context(event)

    assert context.correlation_id == "request-123"


def test_correlation_id_validation_rejects_blank_or_malformed_values():
    assert is_valid_correlation_id("corr-123456") is True
    assert is_valid_correlation_id("") is False
    assert is_valid_correlation_id("   ") is False
    assert is_valid_correlation_id("has spaces") is False
