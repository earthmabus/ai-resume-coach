from __future__ import annotations

from dataclasses import dataclass


STATUS_ANALYSIS_IN_PROGRESS = "ANALYSIS_IN_PROGRESS"
STATUS_PROCESSING = "processing"
STATUS_WAITING = "waiting"
STATUS_QUEUED_PENDING_DISPATCH = "QUEUED_PENDING_DISPATCH"
STATUS_QUEUED = "QUEUED"
STATUS_WORKER_PROCESSING = "WORKER_PROCESSING"
STATUS_RESULT_READY_PENDING_CHILD_DISPATCH = (
    "RESULT_READY_PENDING_CHILD_DISPATCH"
)
STATUS_COMPLETED = "completed"
STATUS_FAILED_RETRYABLE = "FAILED_RETRYABLE"
STATUS_FAILED_PERMANENT = "FAILED_PERMANENT"
STATUS_FAILED_RETRY_EXHAUSTED = "FAILED_RETRY_EXHAUSTED"

TERMINAL_STATUSES = frozenset(
    {
        STATUS_COMPLETED,
        STATUS_FAILED_PERMANENT,
        STATUS_FAILED_RETRY_EXHAUSTED,
    }
)

_ALLOWED_TRANSITIONS = {
    STATUS_ANALYSIS_IN_PROGRESS: frozenset(
        {
            STATUS_QUEUED_PENDING_DISPATCH,
            STATUS_WORKER_PROCESSING,
        }
    ),
    STATUS_PROCESSING: frozenset(
        {
            STATUS_QUEUED_PENDING_DISPATCH,
            STATUS_WORKER_PROCESSING,
        }
    ),
    STATUS_WAITING: frozenset(
        {
            STATUS_QUEUED_PENDING_DISPATCH,
            STATUS_WORKER_PROCESSING,
        }
    ),
    STATUS_QUEUED_PENDING_DISPATCH: frozenset(
        {
            STATUS_QUEUED,
            STATUS_WORKER_PROCESSING,
        }
    ),
    STATUS_QUEUED: frozenset({STATUS_WORKER_PROCESSING}),
    STATUS_WORKER_PROCESSING: frozenset(
        {
            STATUS_WORKER_PROCESSING,
            STATUS_RESULT_READY_PENDING_CHILD_DISPATCH,
            STATUS_COMPLETED,
            STATUS_FAILED_RETRYABLE,
            STATUS_FAILED_PERMANENT,
            STATUS_FAILED_RETRY_EXHAUSTED,
        }
    ),
    STATUS_RESULT_READY_PENDING_CHILD_DISPATCH: frozenset(
        {
            STATUS_WORKER_PROCESSING,
            STATUS_COMPLETED,
        }
    ),
    STATUS_FAILED_RETRYABLE: frozenset({STATUS_WORKER_PROCESSING}),
    STATUS_COMPLETED: frozenset(),
    STATUS_FAILED_PERMANENT: frozenset(),
    STATUS_FAILED_RETRY_EXHAUSTED: frozenset(),
}


@dataclass(frozen=True)
class InvalidWorkflowTransition(ValueError):
    current_status: str
    target_status: str

    def __str__(self) -> str:
        return (
            "Invalid workflow transition: "
            f"{self.current_status!r} -> {self.target_status!r}"
        )


def known_status(status: str | None) -> bool:
    return bool(status) and status in _ALLOWED_TRANSITIONS


def is_terminal(status: str | None) -> bool:
    return status in TERMINAL_STATUSES


def can_transition(current_status: str, target_status: str) -> bool:
    return target_status in _ALLOWED_TRANSITIONS.get(current_status, frozenset())


def assert_transition(current_status: str, target_status: str) -> None:
    if not can_transition(current_status, target_status):
        raise InvalidWorkflowTransition(current_status, target_status)
