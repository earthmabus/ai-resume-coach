from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from core.errors import ResourceConflictError
from features import job_matching


USER_ID = "user-123"
MATCH_ID = "match-123"
REQUEST_ID = "request-123"


def make_event(
    *,
    version: str | None = "2",
) -> dict:
    query_parameters = {}

    if version is not None:
        query_parameters["version"] = version

    return {
        "routeKey": "DELETE /job-match/{id}",
        "pathParameters": {
            "id": MATCH_ID,
        },
        "queryStringParameters": query_parameters,
        "requestContext": {
            "requestId": REQUEST_ID,
            "routeKey": "DELETE /job-match/{id}",
            "http": {
                "method": "DELETE",
                "path": f"/job-match/{MATCH_ID}",
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
        "DeleteItem",
    )


def test_delete_job_match_requires_version(
    monkeypatch,
):
    table = MagicMock()
    monkeypatch.setattr(job_matching, "table", table)

    response = job_matching.delete_job_match(
        make_event(version=None)
    )

    assert response["statusCode"] == 400
    assert "version query parameter is required" in (
        response_body(response)["error"]
    )

    table.get_item.assert_not_called()
    table.delete_item.assert_not_called()


def test_delete_job_match_uses_direct_base_key(
    monkeypatch,
):
    table = MagicMock()
    table.get_item.return_value = {
        "Item": {
            "pk": f"USER#{USER_ID}",
            "sk": f"MATCH#{MATCH_ID}",
            "recordType": "jobMatch",
            "userId": USER_ID,
            "matchId": MATCH_ID,
            "version": 2,
        }
    }
    table.query.return_value = {
        "Items": [],
    }

    monkeypatch.setattr(job_matching, "table", table)

    response = job_matching.delete_job_match(
        make_event(version="2")
    )

    assert response["statusCode"] == 200

    table.get_item.assert_called_once_with(
        Key={
            "pk": f"USER#{USER_ID}",
            "sk": f"MATCH#{MATCH_ID}",
        },
        ConsistentRead=True,
    )

    first_delete = table.delete_item.call_args_list[
        0
    ].kwargs

    assert first_delete["Key"] == {
        "pk": f"USER#{USER_ID}",
        "sk": f"MATCH#{MATCH_ID}",
    }


def test_delete_job_match_removes_children(
    monkeypatch,
):
    table = MagicMock()
    table.get_item.return_value = {
        "Item": {
            "userId": USER_ID,
            "recordType": "jobMatch",
            "version": 2,
        }
    }
    table.query.return_value = {
        "Items": [
            {
                "pk": f"MATCH#{MATCH_ID}",
                "sk": "TAILORING#tailoring-123",
                "userId": USER_ID,
            },
            {
                "pk": f"MATCH#{MATCH_ID}",
                "sk": "INTERVIEW#interview-123",
                "userId": USER_ID,
            },
        ]
    }

    monkeypatch.setattr(job_matching, "table", table)

    response = job_matching.delete_job_match(
        make_event(version="2")
    )
    body = response_body(response)

    assert response["statusCode"] == 200
    assert body["deletedCount"] == 3
    assert body["deletedChildren"] == 2
    assert table.delete_item.call_count == 3


def test_missing_job_match_returns_404(
    monkeypatch,
):
    table = MagicMock()
    table.get_item.return_value = {}

    monkeypatch.setattr(job_matching, "table", table)

    response = job_matching.delete_job_match(
        make_event(version="2")
    )

    assert response["statusCode"] == 404
    table.delete_item.assert_not_called()


def test_stale_job_match_delete_raises_conflict(
    monkeypatch,
):
    table = MagicMock()
    table.get_item.return_value = {
        "Item": {
            "userId": USER_ID,
            "recordType": "jobMatch",
            "version": 3,
        }
    }
    table.delete_item.side_effect = conditional_failure()

    monkeypatch.setattr(job_matching, "table", table)

    with pytest.raises(ResourceConflictError):
        job_matching.delete_job_match(
            make_event(version="2")
        )

    table.query.assert_not_called()
