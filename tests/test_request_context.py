from __future__ import annotations

from core.request_context import build_request_context


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
