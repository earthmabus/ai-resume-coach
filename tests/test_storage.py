from __future__ import annotations

from unittest.mock import MagicMock

from botocore.exceptions import ClientError

from core import storage
from core.outbox import (
    OUTBOX_STATUS_PENDING,
    OUTBOX_STATUS_PREPARING,
)


def conditional_failure(operation: str = "PutItem") -> ClientError:
    return ClientError(
        {
            "Error": {
                "Code": "ConditionalCheckFailedException",
                "Message": "condition failed",
            }
        },
        operation,
    )


def business_item() -> dict:
    return {
        "pk": "USER#user-123",
        "sk": "MATCH#match-123",
        "recordType": "jobMatch",
        "createdRegion": "us-east-1",
        "createdByRequestId": "request-123",
        "createdByRequestHash": "hash-123",
    }


def outbox_item() -> dict:
    return {
        "pk": "OUTBOX#event-123",
        "sk": "OUTBOX#event-123",
        "recordType": "outboxEvent",
        "eventId": "event-123",
        "payloadHash": "payload-hash-123",
        "status": OUTBOX_STATUS_PENDING,
        "createdAt": "2026-07-24T00:00:00+00:00",
        "updatedAt": "2026-07-24T00:00:00+00:00",
        "createdRegion": "us-east-1",
        "createdByRequestId": "request-123",
        "gsi1pk": "OUTBOX_STATUS#PENDING",
        "gsi1sk": "2026-07-24T00:00:00+00:00#event-123",
    }


def test_item_with_owner_region_uses_created_region():
    item = {
        "pk": "USER#user-123",
        "sk": "RESUME#analysis-123",
        "createdRegion": "us-east-1",
    }

    assert storage.item_with_owner_region(item) == {
        **item,
        "ownerRegion": "us-east-1",
    }


def test_item_with_owner_region_preserves_explicit_owner_region():
    item = {
        "pk": "USER#user-123",
        "sk": "RESUME#analysis-123",
        "createdRegion": "us-east-1",
        "ownerRegion": "us-west-2",
    }

    assert storage.item_with_owner_region(item) is item


def test_item_with_owner_region_leaves_legacy_item_without_created_region():
    item = {
        "pk": "USER#user-123",
        "sk": "PROFILE",
    }

    assert storage.item_with_owner_region(item) is item


def test_create_protocol_hides_outbox_until_business_items_exist(monkeypatch):
    table = MagicMock()
    monkeypatch.setattr(storage, "table", table)

    created = storage.put_items_and_outbox_if_absent(
        items=[business_item()],
        outbox_item=outbox_item(),
    )

    assert created is True
    assert table.put_item.call_count == 2

    prepared_outbox = table.put_item.call_args_list[0].kwargs["Item"]
    assert prepared_outbox["status"] == OUTBOX_STATUS_PREPARING
    assert "gsi1pk" not in prepared_outbox
    assert "gsi1sk" not in prepared_outbox

    created_business = table.put_item.call_args_list[1].kwargs["Item"]
    assert created_business["recordType"] == "jobMatch"
    assert created_business["ownerRegion"] == "us-east-1"

    activation = table.update_item.call_args.kwargs
    assert activation["ExpressionAttributeValues"][":pending"] == (
        OUTBOX_STATUS_PENDING
    )
    assert activation["ExpressionAttributeValues"][":gsi1pk"] == (
        "OUTBOX_STATUS#PENDING"
    )


def test_create_protocol_resumes_compatible_partial_attempt(monkeypatch):
    table = MagicMock()
    table.put_item.side_effect = [
        conditional_failure(),
        conditional_failure(),
    ]
    table.get_item.side_effect = [
        {
            "Item": {
                **outbox_item(),
                "status": OUTBOX_STATUS_PREPARING,
                "ownerRegion": "us-east-1",
            }
        },
        {
            "Item": {
                **business_item(),
                "ownerRegion": "us-east-1",
            }
        },
    ]
    monkeypatch.setattr(storage, "table", table)

    assert storage.put_items_and_outbox_if_absent(
        items=[business_item()],
        outbox_item=outbox_item(),
    ) is True

    table.update_item.assert_called_once()


def test_create_protocol_rejects_conflicting_business_item(monkeypatch):
    table = MagicMock()
    table.put_item.side_effect = [None, conditional_failure()]
    table.get_item.return_value = {
        "Item": {
            **business_item(),
            "createdByRequestHash": "different-hash",
            "createdByRequestId": "different-request",
        }
    }
    monkeypatch.setattr(storage, "table", table)

    assert storage.put_items_and_outbox_if_absent(
        items=[business_item()],
        outbox_item=outbox_item(),
    ) is False

    table.update_item.assert_not_called()


def test_create_protocol_accepts_already_active_same_outbox(monkeypatch):
    table = MagicMock()
    table.update_item.side_effect = conditional_failure("UpdateItem")
    table.get_item.return_value = {
        "Item": {
            **outbox_item(),
            "ownerRegion": "us-east-1",
        }
    }
    monkeypatch.setattr(storage, "table", table)

    assert storage.put_items_and_outbox_if_absent(
        items=[business_item()],
        outbox_item=outbox_item(),
    ) is True


def test_update_protocol_activates_after_business_update(monkeypatch):
    table = MagicMock()
    monkeypatch.setattr(storage, "table", table)

    assert storage.update_item_and_put_outbox(
        key={
            "pk": "TAILORING#match-123",
            "sk": "TAILORING#tailoring-123",
        },
        update_expression="SET #status = :pendingDispatch",
        condition_expression="#status = :waiting",
        expression_attribute_names={"#status": "status"},
        expression_attribute_values={
            ":waiting": "waiting",
            ":pendingDispatch": "QUEUED_PENDING_DISPATCH",
        },
        outbox_item=outbox_item(),
    ) is True

    assert table.put_item.call_count == 1
    assert table.update_item.call_count == 2
    business_update = table.update_item.call_args_list[0].kwargs
    activation = table.update_item.call_args_list[1].kwargs
    assert business_update["Key"]["sk"] == "TAILORING#tailoring-123"
    assert activation["Key"]["sk"] == "OUTBOX#event-123"


def test_update_protocol_resumes_after_business_update(monkeypatch):
    table = MagicMock()
    table.update_item.side_effect = [
        conditional_failure("UpdateItem"),
        None,
    ]
    table.get_item.return_value = {
        "Item": {
            "pk": "TAILORING#match-123",
            "sk": "TAILORING#tailoring-123",
            "updatedByRequestId": "request-123",
            "status": "QUEUED_PENDING_DISPATCH",
        }
    }
    monkeypatch.setattr(storage, "table", table)

    assert storage.update_item_and_put_outbox(
        key={
            "pk": "TAILORING#match-123",
            "sk": "TAILORING#tailoring-123",
        },
        update_expression="SET #status = :pendingDispatch",
        condition_expression="#status = :waiting",
        expression_attribute_names={"#status": "status"},
        expression_attribute_values={
            ":waiting": "waiting",
            ":pendingDispatch": "QUEUED_PENDING_DISPATCH",
        },
        outbox_item=outbox_item(),
    ) is True

    assert table.update_item.call_count == 2


def test_update_protocol_rejects_unrelated_completed_update(monkeypatch):
    table = MagicMock()
    table.update_item.side_effect = conditional_failure("UpdateItem")
    table.get_item.return_value = {
        "Item": {
            "pk": "TAILORING#match-123",
            "sk": "TAILORING#tailoring-123",
            "updatedByRequestId": "another-request",
        }
    }
    monkeypatch.setattr(storage, "table", table)

    assert storage.update_item_and_put_outbox(
        key={
            "pk": "TAILORING#match-123",
            "sk": "TAILORING#tailoring-123",
        },
        update_expression="SET #status = :pendingDispatch",
        condition_expression="#status = :waiting",
        expression_attribute_names={"#status": "status"},
        expression_attribute_values={
            ":waiting": "waiting",
            ":pendingDispatch": "QUEUED_PENDING_DISPATCH",
        },
        outbox_item=outbox_item(),
    ) is False
