from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from core.outbox_replay import replay_event


def permanent_item():
    return {
        "pk": "OUTBOX#event-123",
        "sk": "OUTBOX#event-123",
        "eventId": "event-123",
        "status": "FAILED_PERMANENT",
        "createdAt": (
            "2026-07-16T00:00:00+00:00"
        ),
        "deliveryAttempts": 20,
        "version": 10,
    }


def test_replay_event_moves_permanent_failure_to_pending():
    table = MagicMock()

    table.get_item.return_value = {
        "Item": permanent_item(),
    }

    table.update_item.return_value = {
        "Attributes": {
            **permanent_item(),
            "status": "PENDING",
            "replayCount": 1,
        }
    }

    result = replay_event(
        table=table,
        event_id="event-123",
        operator="michael",
        now=(
            "2026-07-16T01:00:00+00:00"
        ),
    )

    assert result["status"] == "PENDING"

    arguments = (
        table.update_item.call_args.kwargs
    )

    assert (
        arguments[
            "ExpressionAttributeValues"
        ][":pendingPk"]
        == "OUTBOX_STATUS#PENDING"
    )

    assert (
        arguments[
            "ExpressionAttributeValues"
        ][":gsi1sk"]
        == (
            "2026-07-16T00:00:00+00:00"
            "#event-123"
        )
    )

    assert (
        "deliveryAttempts = :zero"
        in arguments["UpdateExpression"]
    )


def test_replay_event_rejects_non_terminal_event():
    table = MagicMock()

    table.get_item.return_value = {
        "Item": {
            **permanent_item(),
            "status": "FAILED_RETRYABLE",
        }
    }

    with pytest.raises(
        ValueError,
        match="Only FAILED_PERMANENT",
    ):
        replay_event(
            table=table,
            event_id="event-123",
            operator="michael",
        )


def test_replay_event_reports_concurrent_change():
    table = MagicMock()

    table.get_item.return_value = {
        "Item": permanent_item(),
    }

    table.update_item.side_effect = ClientError(
        {
            "Error": {
                "Code": (
                    "ConditionalCheckFailedException"
                ),
                "Message": "changed",
            }
        },
        "UpdateItem",
    )

    with pytest.raises(
        RuntimeError,
        match="changed before",
    ):
        replay_event(
            table=table,
            event_id="event-123",
            operator="michael",
        )


def test_replay_event_rejects_missing_event():
    table = MagicMock()
    table.get_item.return_value = {}

    with pytest.raises(
        LookupError,
        match="was not found",
    ):
        replay_event(
            table=table,
            event_id="event-123",
            operator="michael",
        )


def test_replay_event_requires_operator():
    table = MagicMock()

    with pytest.raises(
        ValueError,
        match="operator is required",
    ):
        replay_event(
            table=table,
            event_id="event-123",
            operator="",
        )

    table.get_item.assert_not_called()
