import pytest

from core.workflow_state import (
    InvalidWorkflowTransition,
    STATUS_COMPLETED,
    STATUS_FAILED_PERMANENT,
    STATUS_FAILED_RETRYABLE,
    STATUS_FAILED_RETRY_EXHAUSTED,
    STATUS_QUEUED,
    STATUS_QUEUED_PENDING_DISPATCH,
    STATUS_RESULT_READY_PENDING_CHILD_DISPATCH,
    STATUS_WORKER_PROCESSING,
    assert_transition,
    can_transition,
    is_terminal,
    known_status,
)


def test_dispatch_transition_is_allowed():
    assert can_transition(STATUS_QUEUED_PENDING_DISPATCH, STATUS_QUEUED)


def test_worker_claim_transition_is_allowed():
    assert can_transition(STATUS_QUEUED, STATUS_WORKER_PROCESSING)


@pytest.mark.parametrize(
    "target",
    [
        STATUS_COMPLETED,
        STATUS_FAILED_RETRYABLE,
        STATUS_FAILED_PERMANENT,
        STATUS_FAILED_RETRY_EXHAUSTED,
        STATUS_RESULT_READY_PENDING_CHILD_DISPATCH,
    ],
)
def test_worker_outcomes_are_allowed(target):
    assert can_transition(STATUS_WORKER_PROCESSING, target)


def test_retryable_failure_can_be_reclaimed():
    assert can_transition(STATUS_FAILED_RETRYABLE, STATUS_WORKER_PROCESSING)


@pytest.mark.parametrize(
    "terminal",
    [STATUS_COMPLETED, STATUS_FAILED_PERMANENT, STATUS_FAILED_RETRY_EXHAUSTED],
)
def test_terminal_states_cannot_transition(terminal):
    assert is_terminal(terminal)
    assert not can_transition(terminal, STATUS_WORKER_PROCESSING)


def test_invalid_transition_raises_clear_error():
    with pytest.raises(InvalidWorkflowTransition) as captured:
        assert_transition(STATUS_COMPLETED, STATUS_WORKER_PROCESSING)

    assert "completed" in str(captured.value)
    assert "WORKER_PROCESSING" in str(captured.value)


def test_unknown_status_is_not_silently_accepted():
    assert not known_status("MYSTERY")
    with pytest.raises(InvalidWorkflowTransition):
        assert_transition("MYSTERY", STATUS_WORKER_PROCESSING)
