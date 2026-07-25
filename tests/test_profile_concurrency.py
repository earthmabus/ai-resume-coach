from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from core.errors import ResourceConflictError
from features import profile


USER_ID = "user-123"
REQUEST_ID = "request-123"


def make_event(*, body: dict | None = None) -> dict:
    return {
        "routeKey": "PUT /profile",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            body
            or {
                "version": 0,
                "firstName": "",
                "lastName": "",
                "preferredProvider": "openai",
            }
        ),
        "requestContext": {
            "requestId": REQUEST_ID,
            "routeKey": "PUT /profile",
            "http": {
                "method": "PUT",
                "path": "/profile",
            },
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": USER_ID,
                    }
                }
            },
        },
    }


def response_body(response: dict) -> dict:
    return json.loads(response["body"])


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


def test_get_missing_profile_returns_provider_default(monkeypatch):
    mocked_table = MagicMock()
    mocked_table.get_item.return_value = {}
    monkeypatch.setattr(profile, "table", mocked_table)

    response = profile.get_profile(make_event())
    body = response_body(response)

    assert response["statusCode"] == 200
    assert body["version"] == 0
    assert body["userId"] == USER_ID
    assert body["preferredProvider"] == "openai"
    assert body["firstName"] == ""
    assert body["lastName"] == ""
    assert "name" not in body
    assert "currentTitle" not in body
    assert "targetTitle" not in body
    assert "yearsExperience" not in body
    assert "certifications" not in body
    assert "resumeStyle" not in body

    mocked_table.get_item.assert_called_once_with(
        Key={
            "pk": f"USER#{USER_ID}",
            "sk": "PROFILE",
        },
        ConsistentRead=True,
    )


def test_existing_legacy_profile_returns_only_active_contract(monkeypatch):
    mocked_table = MagicMock()
    mocked_table.get_item.return_value = {
        "Item": {
            "pk": f"USER#{USER_ID}",
            "sk": "PROFILE",
            "userId": USER_ID,
            "version": 3,
            "name": "Legacy Name",
            "currentTitle": "Legacy Title",
            "preferredProvider": "rule-based",
        }
    }
    monkeypatch.setattr(profile, "table", mocked_table)

    body = response_body(profile.get_profile(make_event()))

    assert body == {
        "pk": f"USER#{USER_ID}",
        "sk": "PROFILE",
        "recordType": "userProfile",
        "userId": USER_ID,
        "version": 3,
        "firstName": "",
        "lastName": "",
        "preferredProvider": "rule-based",
    }


def test_create_profile_from_version_zero(monkeypatch):
    mocked_table = MagicMock()
    mocked_table.update_item.return_value = {
        "Attributes": {
            "pk": f"USER#{USER_ID}",
            "sk": "PROFILE",
            "recordType": "userProfile",
            "userId": USER_ID,
            "version": 1,
            "firstName": "",
            "lastName": "",
            "preferredProvider": "openai",
        }
    }
    monkeypatch.setattr(profile, "table", mocked_table)

    response = profile.update_profile(make_event())
    body = response_body(response)

    assert response["statusCode"] == 200
    assert body["version"] == 1
    assert body["preferredProvider"] == "openai"
    assert body["firstName"] == ""
    assert body["lastName"] == ""

    call = mocked_table.update_item.call_args.kwargs
    assert call["ExpressionAttributeValues"][":firstName"] == ""
    assert call["ExpressionAttributeValues"][":lastName"] == ""
    assert call["ExpressionAttributeValues"][":expectedVersion"] == 0
    assert "currentTitle" not in call["UpdateExpression"]
    assert "targetTitle" not in call["UpdateExpression"]
    assert "resumeStyle" not in call["UpdateExpression"]


def test_update_profile_with_matching_version(monkeypatch):
    mocked_table = MagicMock()
    mocked_table.update_item.return_value = {
        "Attributes": {
            "userId": USER_ID,
            "version": 4,
            "firstName": "Michael",
            "lastName": "Popovich",
            "preferredProvider": "rule-based",
        }
    }
    monkeypatch.setattr(profile, "table", mocked_table)

    response = profile.update_profile(
        make_event(
            body={
                "version": 3,
                "firstName": "Michael",
                "lastName": "Popovich",
                "preferredProvider": "rule-based",
            }
        )
    )

    assert response["statusCode"] == 200
    assert response_body(response)["version"] == 4
    assert response_body(response)["preferredProvider"] == "rule-based"
    assert response_body(response)["firstName"] == "Michael"
    assert response_body(response)["lastName"] == "Popovich"

    call = mocked_table.update_item.call_args.kwargs
    assert call["ExpressionAttributeValues"][":expectedVersion"] == 3


def test_missing_profile_version_returns_400(monkeypatch):
    mocked_table = MagicMock()
    monkeypatch.setattr(profile, "table", mocked_table)

    response = profile.update_profile(
        make_event(body={"preferredProvider": "openai"})
    )

    assert response["statusCode"] == 400
    assert "version is required" in response_body(response)["error"]
    mocked_table.update_item.assert_not_called()


def test_unsupported_provider_returns_400(monkeypatch):
    mocked_table = MagicMock()
    monkeypatch.setattr(profile, "table", mocked_table)

    response = profile.update_profile(
        make_event(
            body={
                "version": 0,
                "preferredProvider": "unsupported",
            }
        )
    )

    assert response["statusCode"] == 400
    assert "not supported" in response_body(response)["error"]
    mocked_table.update_item.assert_not_called()


def test_stale_profile_version_raises_conflict(monkeypatch):
    mocked_table = MagicMock()
    mocked_table.update_item.side_effect = conditional_failure()
    monkeypatch.setattr(profile, "table", mocked_table)

    with pytest.raises(ResourceConflictError):
        profile.update_profile(
            make_event(
                body={
                    "version": 2,
                    "preferredProvider": "openai",
                }
            )
        )


def test_profile_name_length_is_bounded(monkeypatch):
    mocked_table = MagicMock()
    monkeypatch.setattr(profile, "table", mocked_table)

    response = profile.update_profile(
        make_event(
            body={
                "version": 0,
                "firstName": "x" * 101,
                "lastName": "Popovich",
                "preferredProvider": "openai",
            }
        )
    )

    assert response["statusCode"] == 400
    assert "100 characters or fewer" in response_body(response)["error"]
    mocked_table.update_item.assert_not_called()
