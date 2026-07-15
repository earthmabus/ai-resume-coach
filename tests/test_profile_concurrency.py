from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from core.errors import ResourceConflictError
from features import profile


USER_ID = "user-123"
REQUEST_ID = "request-123"


def make_event(
    *,
    body: dict | None = None,
) -> dict:
    return {
        "routeKey": "PUT /profile",
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(
            body
            or {
                "version": 0,
                "name": "Michael",
                "currentTitle": (
                    "Software Engineering Manager"
                ),
                "targetTitle": (
                    "Director of Software Engineering"
                ),
                "yearsExperience": "15",
                "certifications": "CISSP, CCSP",
                "preferredProvider": "openai",
                "resumeStyle": "executive",
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


def test_get_missing_profile_returns_version_zero(
    monkeypatch,
):
    table = MagicMock()
    table.get_item.return_value = {}

    monkeypatch.setattr(profile, "table", table)

    response = profile.get_profile(make_event())
    body = response_body(response)

    assert response["statusCode"] == 200
    assert body["version"] == 0
    assert body["userId"] == USER_ID

    table.get_item.assert_called_once_with(
        Key={
            "pk": f"USER#{USER_ID}",
            "sk": "PROFILE",
        },
        ConsistentRead=True,
    )


def test_create_profile_from_version_zero(
    monkeypatch,
):
    table = MagicMock()
    table.update_item.return_value = {
        "Attributes": {
            "pk": f"USER#{USER_ID}",
            "sk": "PROFILE",
            "recordType": "userProfile",
            "userId": USER_ID,
            "version": 1,
            "name": "Michael",
        }
    }

    monkeypatch.setattr(profile, "table", table)

    response = profile.update_profile(make_event())
    body = response_body(response)

    assert response["statusCode"] == 200
    assert body["version"] == 1

    call = table.update_item.call_args.kwargs

    assert (
        call["ExpressionAttributeValues"][
            ":expectedVersion"
        ]
        == 0
    )


def test_update_profile_with_matching_version(
    monkeypatch,
):
    table = MagicMock()
    table.update_item.return_value = {
        "Attributes": {
            "userId": USER_ID,
            "version": 4,
            "name": "Michael",
        }
    }

    monkeypatch.setattr(profile, "table", table)

    response = profile.update_profile(
        make_event(
            body={
                "version": 3,
                "name": "Michael",
                "currentTitle": "Senior Manager",
                "targetTitle": "Director",
                "yearsExperience": "15",
                "certifications": "CISSP",
                "preferredProvider": "openai",
                "resumeStyle": "executive",
            }
        )
    )

    assert response["statusCode"] == 200
    assert response_body(response)["version"] == 4

    call = table.update_item.call_args.kwargs

    assert (
        call["ExpressionAttributeValues"][
            ":expectedVersion"
        ]
        == 3
    )


def test_missing_profile_version_returns_400(
    monkeypatch,
):
    table = MagicMock()
    monkeypatch.setattr(profile, "table", table)

    response = profile.update_profile(
        make_event(body={"name": "Michael"})
    )

    assert response["statusCode"] == 400
    assert "version is required" in response_body(
        response
    )["error"]

    table.update_item.assert_not_called()


def test_stale_profile_version_raises_conflict(
    monkeypatch,
):
    table = MagicMock()
    table.update_item.side_effect = conditional_failure()

    monkeypatch.setattr(profile, "table", table)

    with pytest.raises(ResourceConflictError):
        profile.update_profile(
            make_event(
                body={
                    "version": 2,
                    "name": "Michael",
                }
            )
        )
