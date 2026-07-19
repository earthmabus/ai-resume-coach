from core.retry_policy import (
    FailureCategory,
    classify_failure,
    decide_retry,
    receive_attempt,
)


class RateLimitError(Exception):
    status_code = 429


class ServiceUnavailableError(Exception):
    status_code = 503


def test_rate_limit_is_retryable():
    decision = decide_retry(RateLimitError("rate limited"), attempt=2)
    assert decision.category == FailureCategory.RATE_LIMITED
    assert decision.retryable is True
    assert decision.terminal is False


def test_provider_unavailable_is_retryable():
    assert classify_failure(ServiceUnavailableError("down")) == FailureCategory.PROVIDER_UNAVAILABLE


def test_validation_failure_is_permanent():
    decision = decide_retry(ValueError("resume text is missing"), attempt=1)
    assert decision.category == FailureCategory.PERMANENT
    assert decision.retryable is False
    assert decision.terminal is True


def test_retryable_failure_becomes_terminal_when_attempts_exhausted():
    decision = decide_retry(TimeoutError("timed out"), attempt=5, max_attempts=5)
    assert decision.retryable is True
    assert decision.exhausted is True
    assert decision.terminal is True


def test_receive_attempt_reads_sqs_receive_count():
    assert receive_attempt({"attributes": {"ApproximateReceiveCount": "4"}}) == 4
    assert receive_attempt({}) == 1
