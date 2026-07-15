from __future__ import annotations

import json
from unittest.mock import MagicMock

from botocore.exceptions import ClientError

from features import job_matching


USER_ID = "user-123"
REQUEST_ID = "request-123"


def make_event() -> dict:
    return {
        "routeKey": "DELETE /job-matches",
        "requestContext": {
            "requestId": REQUEST_ID,
            "routeKey": "DELETE /job-matches",
            "http": {
                "method": "DELETE",
                "path": "/job-matches",
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


def test_bulk_delete_job_matches_and_children(
    monkeypatch,
):
    table = MagicMock()

    matches = [
        {
            "pk": f"USER#{USER_ID}",
            "sk": "MATCH#match-1",
            "recordType": "jobMatch",
            "userId": USER_ID,
            "matchId": "match-1",
            "version": 2,
        },
        {
            "pk": f"USER#{USER_ID}",
            "sk": "MATCH#match-2",
            "recordType": "jobMatch",
            "userId": USER_ID,
            "matchId": "match-2",
            "version": 3,
        },
    ]

    match_1_children = [
        {
            "pk": "MATCH#match-1",
            "sk": "TAILORING#tailoring-1",
            "recordType": "resumeTailoring",
            "userId": USER_ID,
            "matchId": "match-1",
        },
        {
            "pk": "MATCH#match-1",
            "sk": "INTERVIEW#interview-1",
            "recordType": "interviewPreparation",
            "userId": USER_ID,
            "matchId": "match-1",
        },
    ]

    #
    # Query order:
    # 1. Parent job-match query
    # 2. Children for match-1
    # 3. Children for match-2
    #
    table.query.side_effect = [
        {"Items": matches},
        {"Items": match_1_children},
        {"Items": []},
    ]

    table.delete_item.side_effect = [
        {},  # match-1 tailoring
        {},  # match-1 interview preparation
        {},  # match-1 parent
        conditional_failure(),  # match-2 parent
    ]

    monkeypatch.setattr(
        job_matching,
        "table",
        table,
    )

    response = job_matching.delete_all_job_matches(
        make_event()
    )
    body = response_body(response)

    assert response["statusCode"] == 200
    assert body == {
        "requested": 2,
        "deleted": 1,
        "conflicted": 1,
        "failed": 0,
        "deletedChildren": 2,
        "failedChildren": 0,
        "recordType": "jobMatchBundle",
    }

    assert table.query.call_count == 3
    assert table.delete_item.call_count == 4


def test_child_failure_preserves_parent(
    monkeypatch,
):
    table = MagicMock()

    table.query.side_effect = [
        {
            "Items": [
                {
                    "pk": f"USER#{USER_ID}",
                    "sk": "MATCH#match-1",
                    "recordType": "jobMatch",
                    "userId": USER_ID,
                    "matchId": "match-1",
                    "version": 2,
                }
            ]
        },
        {
            "Items": [
                {
                    "pk": "MATCH#match-1",
                    "sk": "TAILORING#tailoring-1",
                    "userId": USER_ID,
                    "matchId": "match-1",
                }
            ]
        },
    ]

    table.delete_item.side_effect = (
        conditional_failure()
    )

    monkeypatch.setattr(
        job_matching,
        "table",
        table,
    )

    response = job_matching.delete_all_job_matches(
        make_event()
    )
    body = response_body(response)

    assert body["requested"] == 1
    assert body["deleted"] == 0
    assert body["failed"] == 1
    assert body["failedChildren"] == 1

    # Only the child delete was attempted.
    assert table.delete_item.call_count == 1


def test_bulk_delete_empty_job_match_list(
    monkeypatch,
):
    table = MagicMock()
    table.query.return_value = {"Items": []}

    monkeypatch.setattr(
        job_matching,
        "table",
        table,
    )

    response = job_matching.delete_all_job_matches(
        make_event()
    )

    assert response_body(response) == {
        "requested": 0,
        "deleted": 0,
        "conflicted": 0,
        "failed": 0,
        "deletedChildren": 0,
        "failedChildren": 0,
        "recordType": "jobMatchBundle",
    }
