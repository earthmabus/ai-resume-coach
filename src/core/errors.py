class ApplicationError(Exception):
    status_code = 500
    error_code = "INTERNAL_ERROR"
    public_message = "An unexpected error occurred"


class ValidationError(ApplicationError):
    status_code = 400
    error_code = "VALIDATION_ERROR"


class IdempotencyKeyRequiredError(ApplicationError):
    status_code = 400
    error_code = "IDEMPOTENCY_KEY_REQUIRED"


class IdempotencyConflictError(ApplicationError):
    status_code = 409
    error_code = "IDEMPOTENCY_KEY_REUSED"


class ResourceConflictError(ApplicationError):
    status_code = 409
    error_code = "RESOURCE_VERSION_CONFLICT"


class ResourceNotFoundError(ApplicationError):
    status_code = 404
    error_code = "RESOURCE_NOT_FOUND"


class ForbiddenError(ApplicationError):
    status_code = 403
    error_code = "FORBIDDEN"
