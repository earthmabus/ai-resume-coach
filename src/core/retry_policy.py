from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class FailureCategory(str, Enum):
    RATE_LIMITED = "RATE_LIMITED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    TRANSIENT_INFRASTRUCTURE = "TRANSIENT_INFRASTRUCTURE"
    PERMANENT = "PERMANENT"


@dataclass(frozen=True)
class RetryDecision:
    category: FailureCategory
    retryable: bool
    exhausted: bool
    attempt: int
    max_attempts: int

    @property
    def terminal(self) -> bool:
        return not self.retryable or self.exhausted


DEFAULT_MAX_ATTEMPTS = 5


def _status_code(error: BaseException) -> int | None:
    for attribute in ("status_code", "status", "http_status"):
        value = getattr(error, attribute, None)
        if isinstance(value, int):
            return value

    response = getattr(error, "response", None)
    if isinstance(response, dict):
        metadata = response.get("ResponseMetadata", {})
        value = metadata.get("HTTPStatusCode")
        if isinstance(value, int):
            return value

    return None


def classify_failure(error: BaseException) -> FailureCategory:
    status = _status_code(error)
    name = type(error).__name__.lower()
    message = str(error).lower()

    if status == 429 or "ratelimit" in name or "rate limit" in message:
        return FailureCategory.RATE_LIMITED

    if status in {502, 503, 504} or any(
        token in name
        for token in ("serviceunavailable", "apiconnection", "timeout")
    ) or any(
        token in message
        for token in ("service unavailable", "temporarily unavailable", "timed out")
    ):
        return FailureCategory.PROVIDER_UNAVAILABLE

    if status is not None and status >= 500:
        return FailureCategory.TRANSIENT_INFRASTRUCTURE

    if isinstance(error, (TimeoutError, ConnectionError, OSError)):
        return FailureCategory.TRANSIENT_INFRASTRUCTURE

    if isinstance(error, (ValueError, TypeError, KeyError)):
        return FailureCategory.PERMANENT

    if status is not None and 400 <= status < 500:
        return FailureCategory.PERMANENT

    return FailureCategory.TRANSIENT_INFRASTRUCTURE


def decide_retry(
    error: BaseException,
    *,
    attempt: int,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> RetryDecision:
    normalized_attempt = max(1, int(attempt))
    normalized_max = max(1, int(max_attempts))
    category = classify_failure(error)
    retryable = category is not FailureCategory.PERMANENT

    return RetryDecision(
        category=category,
        retryable=retryable,
        exhausted=retryable and normalized_attempt >= normalized_max,
        attempt=normalized_attempt,
        max_attempts=normalized_max,
    )


def receive_attempt(record: dict[str, Any]) -> int:
    attributes = record.get("attributes") or {}
    raw = attributes.get("ApproximateReceiveCount", "1")

    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 1
