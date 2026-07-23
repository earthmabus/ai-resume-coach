from __future__ import annotations

import itertools

import pytest

from core.workflow_state import (
    InvalidWorkflowTransition,
    STATUS_ANALYSIS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_FAILED_PERMANENT,
    STATUS_FAILED_RETRYABLE,
    STATUS_FAILED_RETRY_EXHAUSTED,
    STATUS_PROCESSING,
    STATUS_QUEUED,
    STATUS_QUEUED_PENDING_DISPATCH,
    STATUS_RESULT_READY_PENDING_CHILD_DISPATCH,
    STATUS_WAITING,
    STATUS_WORKER_PROCESSING,
    assert_transition,
    can_transition,
    is_terminal,
    known_status,
)


STATUSES = (
    STATUS_ANALYSIS_IN_PROGRESS,
    STATUS_PROCESSING,
    STATUS_WAITING,
    STATUS_QUEUED_PENDING_DISPATCH,
    STATUS_QUEUED,
    STATUS_WORKER_PROCESSING,
    STATUS_RESULT_READY_PENDING_CHILD_DISPATCH,
    STATUS_COMPLETED,
    STATUS_FAILED_RETRYABLE,
    STATUS_FAILED_PERMANENT,
    STATUS_FAILED_RETRY_EXHAUSTED,
)

EXPECTED = {
    STATUS_ANALYSIS_IN_PROGRESS: {
        STATUS_QUEUED_PENDING_DISPATCH,
        STATUS_WORKER_PROCESSING,
    },
    STATUS_PROCESSING: {
        STATUS_QUEUED_PENDING_DISPATCH,
        STATUS_WORKER_PROCESSING,
    },
    STATUS_WAITING: {
        STATUS_QUEUED_PENDING_DISPATCH,
        STATUS_WORKER_PROCESSING,
    },
    STATUS_QUEUED_PENDING_DISPATCH: {
        STATUS_QUEUED,
        STATUS_WORKER_PROCESSING,
    },
    STATUS_QUEUED: {STATUS_WORKER_PROCESSING},
    STATUS_WORKER_PROCESSING: {
        STATUS_WORKER_PROCESSING,
        STATUS_RESULT_READY_PENDING_CHILD_DISPATCH,
        STATUS_COMPLETED,
        STATUS_FAILED_RETRYABLE,
        STATUS_FAILED_PERMANENT,
        STATUS_FAILED_RETRY_EXHAUSTED,
    },
    STATUS_RESULT_READY_PENDING_CHILD_DISPATCH: {
        STATUS_WORKER_PROCESSING,
        STATUS_COMPLETED,
    },
    STATUS_FAILED_RETRYABLE: {STATUS_WORKER_PROCESSING},
    STATUS_COMPLETED: set(),
    STATUS_FAILED_PERMANENT: set(),
    STATUS_FAILED_RETRY_EXHAUSTED: set(),
}


@pytest.mark.parametrize("status", STATUSES)
def test_every_documented_status_is_known(status):
    assert known_status(status)


@pytest.mark.parametrize("current,target", list(itertools.product(STATUSES, STATUSES)))
def test_transition_matrix_matches_documented_contract(current, target):
    expected = target in EXPECTED[current]

    assert can_transition(current, target) is expected

    if expected:
        assert_transition(current, target)
    else:
        with pytest.raises(InvalidWorkflowTransition):
            assert_transition(current, target)


@pytest.mark.parametrize(
    "status",
    [STATUS_COMPLETED, STATUS_FAILED_PERMANENT, STATUS_FAILED_RETRY_EXHAUSTED],
)
def test_terminal_states_have_no_outbound_edges(status):
    assert is_terminal(status)
    assert EXPECTED[status] == set()


@pytest.mark.parametrize(
    "status",
    set(STATUSES)
    - {
        STATUS_COMPLETED,
        STATUS_FAILED_PERMANENT,
        STATUS_FAILED_RETRY_EXHAUSTED,
    },
)
def test_nonterminal_states_are_not_reported_terminal(status):
    assert not is_terminal(status)


@pytest.mark.parametrize("unknown", [None, "", "UNKNOWN", "queued", "COMPLETED"])
def test_unknown_statuses_are_never_accepted(unknown):
    assert not known_status(unknown)
    for target in STATUSES:
        assert not can_transition(unknown, target)
