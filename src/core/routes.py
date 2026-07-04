from core.responses import build_response

def route_request(event, routes):
    route = event.get("routeKey")
    handler = routes.get(route)

    if not handler:
        return build_response(404, {"error": "Route not found", "route": route})

    return handler(event)
