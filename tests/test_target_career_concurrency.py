from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from core.errors import ResourceConflictError
from features import target_career


USER_ID = "user-123"
REQUEST_ID = "request-123"


def make_event(
    *,
    body: dict | None = None,
) -> dict:
    return {
        "routeKey": "PUT /target-career",
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(
            body
            or {
                "version": 0,
                "roleTitle": (
                    "Director of Software Engineering"
                ),
                "industry": "Technology",
                "seniorityLevel": "Director",
                "workEnvironment": "Remote",
                "keyResponsibilities": (
                    "Lead engineering organizations"
                ),
                "requiredSkills": "Cloud, security, AI",
                "certifications": "CISSP, CCSP",
                "physicalRequirements": "",
                "technicalRequirements": "AWS",
                "leadershipRequirements": (
                    "Organizational leadership"
                ),
                "careerGoalSummary": (
                    "Lead engineering transformation"
                ),
            }
        ),
        "requestContext": {
            "requestId": REQUEST_ID,
            "routeKey": "PUT /target-career",
            "http": {
                "method": "PUT",
                "path": "/target-career",
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


def test_get_missing_target_career_returns_version_zero(
    monkeypatch,
):
    table = MagicMock()
    table.get_item.return_value = {}

    monkeypatch.setattr(target_career, "table", table)

    response = target_career.get_target_career(
        make_event()
    )
    body = response_body(response)

    assert response["statusCode"] == 200
    assert body["version"] == 0
    assert body["userId"] == USER_ID


def test_create_target_career_from_version_zero(
    monkeypatch,
):
    table = MagicMock()
    table.update_item.return_value = {
        "Attributes": {
            "recordType": "targetCareer",
            "targetCareerId": (
                f"target-career-{USER_ID}"
            ),
            "userId": USER_ID,
            "version": 1,
            "roleTitle": (
                "Director of Software Engineering"
            ),
            "industry": "Technology",
        }
    }

    monkeypatch.setattr(target_career, "table", table)

    response = target_career.update_target_career(
        make_event()
    )
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


def test_update_target_career_with_matching_version(
    monkeypatch,
):
    table = MagicMock()
    table.update_item.return_value = {
        "Attributes": {
            "recordType": "targetCareer",
            "targetCareerId": (
                f"target-career-{USER_ID}"
            ),
            "userId": USER_ID,
            "version": 5,
            "roleTitle": "Engineering Director",
            "industry": "Healthcare",
        }
    }

    monkeypatch.setattr(target_career, "table", table)

    response = target_career.update_target_career(
        make_event(
            body={
                "version": 4,
                "roleTitle": "Engineering Director",
                "industry": "Healthcare",
            }
        )
    )

    assert response["statusCode"] == 200
    assert response_body(response)["version"] == 5


def test_missing_target_career_version_returns_400(
    monkeypatch,
):
    table = MagicMock()
    monkeypatch.setattr(target_career, "table", table)

    response = target_career.update_target_career(
        make_event(
            body={
                "roleTitle": "Director",
                "industry": "Technology",
            }
        )
    )

    assert response["statusCode"] == 400
    assert "version is required" in response_body(
        response
    )["error"]

    table.update_item.assert_not_called()


def test_stale_target_career_version_raises_conflict(
    monkeypatch,
):
    table = MagicMock()
    table.update_item.side_effect = conditional_failure()

    monkeypatch.setattr(target_career, "table", table)

    with pytest.raises(ResourceConflictError):
        target_career.update_target_career(
            make_event(
                body={
                    "version": 2,
                    "roleTitle": "Director",
                    "industry": "Technology",
                }
            )
        )
