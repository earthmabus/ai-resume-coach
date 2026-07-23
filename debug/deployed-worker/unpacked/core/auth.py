def current_user_id(event):
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
    )

    user_id = claims.get("sub")

    if not user_id:
        raise ValueError("Unauthorized: missing user identity")

    return user_id

def assert_item_owner(item, user_id):
    if item.get("userId") != user_id:
        raise PermissionError("Forbidden")
