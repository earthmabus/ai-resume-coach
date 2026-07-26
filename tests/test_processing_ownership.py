import pytest

from core.processing_ownership import (
    ProcessingOwnershipError,
    ProcessingOwnershipStatus,
    evaluate_processing_ownership,
    require_processing_ownership,
)


def test_persisted_owner_authorizes_matching_worker_and_message():
    decision = evaluate_processing_ownership(
        current_region="us-east-1",
        message_owner_region="us-east-1",
        persisted_owner_region="us-east-1",
    )

    assert decision.status == ProcessingOwnershipStatus.AUTHORIZED
    assert decision.authoritative_owner_region == "us-east-1"


def test_persisted_owner_rejects_non_owner_worker():
    decision = evaluate_processing_ownership(
        current_region="us-west-2",
        message_owner_region="us-east-1",
        persisted_owner_region="us-east-1",
    )

    assert decision.status == ProcessingOwnershipStatus.REJECTED
    assert not decision.authorized


def test_persisted_owner_rejects_conflicting_message_metadata():
    decision = evaluate_processing_ownership(
        current_region="us-west-2",
        message_owner_region="us-west-2",
        persisted_owner_region="us-east-1",
    )

    assert decision.status == ProcessingOwnershipStatus.REJECTED
    assert "conflicts" in decision.reason


def test_message_owner_is_authoritative_when_persisted_record_is_legacy():
    decision = evaluate_processing_ownership(
        current_region="us-west-2",
        message_owner_region="us-west-2",
        persisted_owner_region="",
    )

    assert decision.status == ProcessingOwnershipStatus.AUTHORIZED
    assert decision.authoritative_owner_region == "us-west-2"


def test_legacy_message_and_record_remain_locally_processable():
    decision = evaluate_processing_ownership(
        current_region="us-east-1",
        message_owner_region="",
        persisted_owner_region="",
    )

    assert decision.status == ProcessingOwnershipStatus.LEGACY_LOCAL
    assert decision.authorized


def test_require_processing_ownership_fails_closed():
    with pytest.raises(ProcessingOwnershipError) as error:
        require_processing_ownership(
            current_region="us-west-2",
            message_owner_region="us-east-1",
            persisted_owner_region="us-east-1",
        )

    assert error.value.decision.authoritative_owner_region == "us-east-1"
