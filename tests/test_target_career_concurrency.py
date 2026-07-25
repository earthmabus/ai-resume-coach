from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from core.errors import ResourceConflictError
from features import target_career


USER_ID = "user-123"
CAREER_ID = "career-123"
REQUEST_ID = "request-123"


def make_event(*, route_key, body=None, career_id=None):
    event = {
        "routeKey": route_key,
        "headers": {"Content-Type": "application/json"},
        "requestContext": {
            "requestId": REQUEST_ID,
            "routeKey": route_key,
            "http": {"method": route_key.split()[0], "path": "/target-careers"},
            "authorizer": {"jwt": {"claims": {"sub": USER_ID}}},
        },
    }
    if body is not None:
        event["body"] = json.dumps(body)
    if career_id is not None:
        event["pathParameters"] = {"id": career_id}
    return event


def response_body(response):
    return json.loads(response["body"])


def conditional_failure(operation="UpdateItem"):
    return ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "Condition failed"}},
        operation,
    )


def career_payload(version=None):
    payload = {
        "roleTitle": "Director of Software Engineering",
        "industry": "Technology",
        "seniorityLevel": "Director",
        "workEnvironment": "Remote",
        "keyResponsibilities": "Lead engineering organizations",
        "requiredSkills": "Cloud, security, AI",
        "certifications": "CISSP",
        "physicalRequirements": "",
        "technicalRequirements": "AWS",
        "leadershipRequirements": "Organizational leadership",
        "careerGoalSummary": "Lead engineering transformation",
    }
    if version is not None:
        payload["version"] = version
    return payload


def test_list_target_careers_returns_collection(monkeypatch):
    table = MagicMock()
    table.query.return_value = {"Items": [{"targetCareerId": CAREER_ID, "createdAt": "2026-01-01"}]}
    monkeypatch.setattr(target_career, "table", table)

    response = target_career.list_target_careers(make_event(route_key="GET /target-careers"))

    assert response["statusCode"] == 200
    assert response_body(response)["targetCareers"][0]["targetCareerId"] == CAREER_ID


@patch("features.target_career.uuid.uuid4", return_value=CAREER_ID)
def test_create_target_career_uses_collection_key(mock_uuid, monkeypatch):
    table = MagicMock()
    monkeypatch.setattr(target_career, "table", table)

    response = target_career.create_target_career(
        make_event(route_key="POST /target-careers", body=career_payload())
    )

    assert response["statusCode"] == 201
    item = table.put_item.call_args.kwargs["Item"]
    assert item["sk"] == f"TARGET_CAREER#{CAREER_ID}"
    assert item["version"] == 1


def test_get_target_career_by_id(monkeypatch):
    table = MagicMock()
    table.get_item.return_value = {"Item": {"targetCareerId": CAREER_ID, "userId": USER_ID, "version": 1}}
    monkeypatch.setattr(target_career, "table", table)

    response = target_career.get_target_career(
        make_event(route_key="GET /target-careers/{id}", career_id=CAREER_ID)
    )

    assert response["statusCode"] == 200
    assert response_body(response)["targetCareerId"] == CAREER_ID


def test_update_target_career_with_matching_version(monkeypatch):
    table = MagicMock()
    table.update_item.return_value = {"Attributes": {"targetCareerId": CAREER_ID, "version": 2}}
    monkeypatch.setattr(target_career, "table", table)

    response = target_career.update_target_career(
        make_event(route_key="PUT /target-careers/{id}", career_id=CAREER_ID, body=career_payload(version=1))
    )

    assert response["statusCode"] == 200
    assert response_body(response)["version"] == 2


def test_stale_update_raises_conflict(monkeypatch):
    table = MagicMock()
    table.update_item.side_effect = conditional_failure()
    monkeypatch.setattr(target_career, "table", table)

    with pytest.raises(ResourceConflictError):
        target_career.update_target_career(
            make_event(route_key="PUT /target-careers/{id}", career_id=CAREER_ID, body=career_payload(version=1))
        )


def test_delete_target_career_uses_version(monkeypatch):
    table = MagicMock()
    monkeypatch.setattr(target_career, "table", table)

    response = target_career.delete_target_career(
        make_event(route_key="DELETE /target-careers/{id}", career_id=CAREER_ID, body={"version": 3})
    )

    assert response["statusCode"] == 200
    assert response_body(response)["deleted"] is True
    values = table.delete_item.call_args.kwargs["ExpressionAttributeValues"]
    assert values[":expectedVersion"] == 3
