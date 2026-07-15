from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from core.errors import IdempotencyConflictError
from core.idempotency import (
    DISPOSITION_REPLAY_COMPLETED,
    DISPOSITION_REPLAY_IN_PROGRESS,
    DISPOSITION_RESERVED,
    STATUS_COMPLETED,
    STATUS_FAILED_RETRYABLE,
    STATUS_IN_PROGRESS,
    canonical_json,
    complete_request,
    idempotency_key_hash,
    idempotency_keys,
    mark_request_retryable,
    request_fingerprint,
    reserve_request,
)


USER_ID = "user-123"
OPERATION = "ANALYZE_UPLOADED_RESUME"
IDEMPOTENCY_KEY = "12345678-1234-1234-1234-123456789012"
REQUEST_HASH = "request-hash-123"
RESOURCE_ID = "analysis-123"
REQUEST_ID = "request-123"
REGION = "us-east-1"


def conditional_failure() -> ClientError:
    return ClientError(
        {
            "Error": {
                "Code": "ConditionalCheckFailedException",
                "Message": "Condition failed",
            }
        },
        "UpdateItem",
    )


def test_canonical_json_ignores_dictionary_field_order():
    first = {
        "resumeName": "Resume",
        "documentKey": "users/1/file.pdf",
    }
    second = {
        "documentKey": "users/1/file.pdf",
        "resumeName": "Resume",
    }

    assert canonical_json(first) == canonical_json(second)


def test_request_fingerprint_is_stable_for_field_order():
    first = request_fingerprint(
        user_id=USER_ID,
        operation=OPERATION,
        body={
            "resumeName": "Resume",
            "documentKey": "users/1/file.pdf",
        },
    )
    second = request_fingerprint(
        user_id=USER_ID,
        operation=OPERATION,
        body={
            "documentKey": "users/1/file.pdf",
            "resumeName": "Resume",
        },
    )

    assert first == second


def test_request_fingerprint_changes_for_different_body():
    first = request_fingerprint(
        user_id=USER_ID,
        operation=OPERATION,
        body={"resumeName": "Resume A"},
    )
    second = request_fingerprint(
        user_id=USER_ID,
        operation=OPERATION,
        body={"resumeName": "Resume B"},
    )

    assert first != second


def test_request_fingerprint_changes_for_different_user():
    first = request_fingerprint(
        user_id="user-1",
        operation=OPERATION,
        body={"resumeName": "Resume"},
    )
    second = request_fingerprint(
        user_id="user-2",
        operation=OPERATION,
        body={"resumeName": "Resume"},
    )

    assert first != second


def test_request_fingerprint_changes_for_different_operation():
    first = request_fingerprint(
        user_id=USER_ID,
        operation="ANALYZE_UPLOADED_RESUME",
        body={"resumeName": "Resume"},
    )
    second = request_fingerprint(
        user_id=USER_ID,
        operation="MATCH_JOB_DESCRIPTION",
        body={"resumeName": "Resume"},
    )

    assert first != second


def test_idempotency_key_is_hashed_before_storage():
    hashed = idempotency_key_hash(IDEMPOTENCY_KEY)

    assert hashed != IDEMPOTENCY_KEY
    assert len(hashed) == 64


def test_idempotency_keys_scope_key_to_user_and_operation():
    pk, sk = idempotency_keys(
        user_id=USER_ID,
        operation=OPERATION,
        idempotency_key=IDEMPOTENCY_KEY,
    )

    assert pk == f"USER#{USER_ID}"
    assert sk.startswith(f"IDEMPOTENCY#{OPERATION}#")
    assert IDEMPOTENCY_KEY not in sk


@patch("core.idempotency.put_item_if_absent")
def test_first_request_is_reserved(mock_put_item_if_absent):
    mock_put_item_if_absent.return_value = True

    reservation = reserve_request(
        user_id=USER_ID,
        operation=OPERATION,
        idempotency_key=IDEMPOTENCY_KEY,
        request_hash=REQUEST_HASH,
        resource_id=RESOURCE_ID,
        request_id=REQUEST_ID,
        region=REGION,
    )

    assert reservation.disposition == DISPOSITION_RESERVED
    assert reservation.resource_id == RESOURCE_ID

    stored_item = mock_put_item_if_absent.call_args.args[0]

    assert stored_item["status"] == STATUS_IN_PROGRESS
    assert stored_item["resourceId"] == RESOURCE_ID
    assert stored_item["requestHash"] == REQUEST_HASH
    assert stored_item["version"] == 1
    assert stored_item["createdRegion"] == REGION
    assert stored_item["lastUpdatedRegion"] == REGION
    assert stored_item["idempotencyKeyHash"] != IDEMPOTENCY_KEY
    assert IDEMPOTENCY_KEY not in stored_item.values()


@patch("core.idempotency.get_item_strong")
@patch("core.idempotency.put_item_if_absent")
def test_completed_request_replays_stored_response(
    mock_put_item_if_absent,
    mock_get_item_strong,
):
    mock_put_item_if_absent.return_value = False
    mock_get_item_strong.return_value = {
        "requestHash": REQUEST_HASH,
        "resourceId": RESOURCE_ID,
        "status": STATUS_COMPLETED,
        "responseStatusCode": 202,
        "responseBody": {
            "analysisId": RESOURCE_ID,
            "status": "processing",
        },
    }

    reservation = reserve_request(
        user_id=USER_ID,
        operation=OPERATION,
        idempotency_key=IDEMPOTENCY_KEY,
        request_hash=REQUEST_HASH,
        resource_id="different-proposed-id",
        request_id=REQUEST_ID,
        region=REGION,
    )

    assert reservation.disposition == DISPOSITION_REPLAY_COMPLETED
    assert reservation.resource_id == RESOURCE_ID
    assert reservation.status_code == 202
    assert reservation.response_body == {
        "analysisId": RESOURCE_ID,
        "status": "processing",
    }


@patch("core.idempotency.get_item_strong")
@patch("core.idempotency.put_item_if_absent")
def test_in_progress_request_returns_same_resource(
    mock_put_item_if_absent,
    mock_get_item_strong,
):
    mock_put_item_if_absent.return_value = False
    mock_get_item_strong.return_value = {
        "requestHash": REQUEST_HASH,
        "resourceId": RESOURCE_ID,
        "status": STATUS_IN_PROGRESS,
    }

    reservation = reserve_request(
        user_id=USER_ID,
        operation=OPERATION,
        idempotency_key=IDEMPOTENCY_KEY,
        request_hash=REQUEST_HASH,
        resource_id="different-proposed-id",
        request_id=REQUEST_ID,
        region=REGION,
    )

    assert reservation.disposition == DISPOSITION_REPLAY_IN_PROGRESS
    assert reservation.resource_id == RESOURCE_ID
    assert reservation.status_code == 202


@patch("core.idempotency.get_item_strong")
@patch("core.idempotency.put_item_if_absent")
def test_reusing_key_with_different_payload_raises_conflict(
    mock_put_item_if_absent,
    mock_get_item_strong,
):
    mock_put_item_if_absent.return_value = False
    mock_get_item_strong.return_value = {
        "requestHash": "different-request-hash",
        "resourceId": RESOURCE_ID,
        "status": STATUS_COMPLETED,
    }

    with pytest.raises(IdempotencyConflictError):
        reserve_request(
            user_id=USER_ID,
            operation=OPERATION,
            idempotency_key=IDEMPOTENCY_KEY,
            request_hash=REQUEST_HASH,
            resource_id=RESOURCE_ID,
            request_id=REQUEST_ID,
            region=REGION,
        )


@patch("core.idempotency.table")
@patch("core.idempotency.get_item_strong")
@patch("core.idempotency.put_item_if_absent")
def test_failed_retryable_request_can_be_reacquired(
    mock_put_item_if_absent,
    mock_get_item_strong,
    mock_table,
):
    mock_put_item_if_absent.return_value = False
    mock_get_item_strong.return_value = {
        "requestHash": REQUEST_HASH,
        "resourceId": RESOURCE_ID,
        "status": STATUS_FAILED_RETRYABLE,
    }

    reservation = reserve_request(
        user_id=USER_ID,
        operation=OPERATION,
        idempotency_key=IDEMPOTENCY_KEY,
        request_hash=REQUEST_HASH,
        resource_id="different-proposed-id",
        request_id=REQUEST_ID,
        region=REGION,
    )

    assert reservation.disposition == DISPOSITION_RESERVED
    assert reservation.resource_id == RESOURCE_ID
    mock_table.update_item.assert_called_once()


@patch("core.idempotency.table")
def test_failed_retryable_reacquire_race_returns_in_progress(
    mock_table,
):
    mock_table.update_item.side_effect = conditional_failure()

    existing = {
        "requestHash": REQUEST_HASH,
        "resourceId": RESOURCE_ID,
        "status": STATUS_FAILED_RETRYABLE,
    }
    raced = {
        "requestHash": REQUEST_HASH,
        "resourceId": RESOURCE_ID,
        "status": STATUS_IN_PROGRESS,
    }

    with (
        patch(
            "core.idempotency.put_item_if_absent",
            return_value=False,
        ),
        patch(
            "core.idempotency.get_item_strong",
            side_effect=[existing, raced],
        ),
    ):
        reservation = reserve_request(
            user_id=USER_ID,
            operation=OPERATION,
            idempotency_key=IDEMPOTENCY_KEY,
            request_hash=REQUEST_HASH,
            resource_id="different-proposed-id",
            request_id=REQUEST_ID,
            region=REGION,
        )

    assert reservation.disposition == DISPOSITION_REPLAY_IN_PROGRESS
    assert reservation.resource_id == RESOURCE_ID


@patch("core.idempotency.table")
def test_complete_request_updates_record(mock_table):
    complete_request(
        user_id=USER_ID,
        operation=OPERATION,
        idempotency_key=IDEMPOTENCY_KEY,
        request_hash=REQUEST_HASH,
        resource_id=RESOURCE_ID,
        request_id=REQUEST_ID,
        region=REGION,
        status_code=202,
        response_body={
            "analysisId": RESOURCE_ID,
            "status": "processing",
        },
    )

    mock_table.update_item.assert_called_once()

    call = mock_table.update_item.call_args.kwargs

    assert (
        call["ExpressionAttributeValues"][":completed"]
        == STATUS_COMPLETED
    )
    assert (
        call["ExpressionAttributeValues"][":resourceId"]
        == RESOURCE_ID
    )
    assert (
        call["ExpressionAttributeValues"][":responseStatusCode"]
        == 202
    )


@patch("core.idempotency.table")
def test_complete_request_treats_matching_completed_record_as_success(
    mock_table,
):
    mock_table.update_item.side_effect = conditional_failure()

    with patch(
        "core.idempotency.get_item_strong",
        return_value={
            "status": STATUS_COMPLETED,
            "requestHash": REQUEST_HASH,
            "resourceId": RESOURCE_ID,
        },
    ):
        complete_request(
            user_id=USER_ID,
            operation=OPERATION,
            idempotency_key=IDEMPOTENCY_KEY,
            request_hash=REQUEST_HASH,
            resource_id=RESOURCE_ID,
            request_id=REQUEST_ID,
            region=REGION,
            status_code=202,
            response_body={
                "analysisId": RESOURCE_ID,
                "status": "processing",
            },
        )


@patch("core.idempotency.table")
def test_mark_request_retryable_updates_record(mock_table):
    mark_request_retryable(
        user_id=USER_ID,
        operation=OPERATION,
        idempotency_key=IDEMPOTENCY_KEY,
        request_hash=REQUEST_HASH,
        resource_id=RESOURCE_ID,
        request_id=REQUEST_ID,
        region=REGION,
    )

    mock_table.update_item.assert_called_once()

    call = mock_table.update_item.call_args.kwargs

    assert (
        call["ExpressionAttributeValues"][":failedRetryable"]
        == STATUS_FAILED_RETRYABLE
    )
    assert (
        call["ExpressionAttributeValues"][":resourceId"]
        == RESOURCE_ID
    )
