from __future__ import annotations

from core.storage import item_with_owner_region


def test_item_with_owner_region_uses_created_region():
    item = {
        "pk": "USER#user-123",
        "sk": "RESUME#analysis-123",
        "createdRegion": "us-east-1",
    }

    assert item_with_owner_region(item) == {
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

    assert item_with_owner_region(item) is item


def test_item_with_owner_region_leaves_legacy_item_without_created_region():
    item = {
        "pk": "USER#user-123",
        "sk": "PROFILE",
    }

    assert item_with_owner_region(item) is item
