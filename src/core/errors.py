from __future__ import annotations


class ApplicationError(Exception):
    status_code = 500
    error_code = "INTERNAL_ERROR"
    default_message = "An unexpected error occurred"

    def __init__(self, message: str | None = None):
        self.public_message = message or self.default_message
        super().__init__(self.public_message)


class ValidationError(ApplicationError):
    status_code = 400
    error_code = "VALIDATION_ERROR"
    default_message = "The request is invalid"


class IdempotencyKeyRequiredError(ApplicationError):
    status_code = 400
    error_code = "IDEMPOTENCY_KEY_REQUIRED"
    default_message = "Idempotency-Key is required for this operation"


class IdempotencyConflictError(ApplicationError):
    status_code = 409
    error_code = "IDEMPOTENCY_KEY_REUSED"
    default_message = (
        "The Idempotency-Key was already used for a different request"
    )


class ResourceConflictError(ApplicationError):
    status_code = 409
    error_code = "RESOURCE_VERSION_CONFLICT"
    default_message = "The resource was changed by another request"


class ResourceNotFoundError(ApplicationError):
    status_code = 404
    error_code = "RESOURCE_NOT_FOUND"
    default_message = "The requested resource was not found"


class ForbiddenError(ApplicationError):
    status_code = 403
    error_code = "FORBIDDEN"
    default_message = "You are not permitted to access this resource"
