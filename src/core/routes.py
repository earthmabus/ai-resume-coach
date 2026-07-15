from __future__ import annotations

import logging
from typing import Any, Callable

from core.errors import ApplicationError
from core.responses import build_response


logger = logging.getLogger(__name__)


def _request_id(event: dict[str, Any]) -> str | None:
    return event.get("requestContext", {}).get("requestId")


def route_request(
    event: dict[str, Any],
    routes: dict[str, Callable],
):
    route = event.get("routeKey")
    handler = routes.get(route)

    if not handler:
        return build_response(
            404,
            {
                "error": {
                    "code": "ROUTE_NOT_FOUND",
                    "message": "Route not found",
                    "requestId": _request_id(event),
                }
            },
        )

    try:
        return handler(event)
    except ApplicationError as error:
        logger.warning(
            "Application request failed",
            extra={
                "route": route,
                "requestId": _request_id(event),
                "errorCode": error.error_code,
            },
        )

        return build_response(
            error.status_code,
            {
                "error": {
                    "code": error.error_code,
                    "message": error.public_message,
                    "requestId": _request_id(event),
                }
            },
        )
    except Exception:
        logger.exception(
            "Unhandled application error",
            extra={
                "route": route,
                "requestId": _request_id(event),
            },
        )

        return build_response(
            500,
            {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "requestId": _request_id(event),
                }
            },
        )
