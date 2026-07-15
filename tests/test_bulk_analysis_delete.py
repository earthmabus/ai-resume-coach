from __future__ import annotations

import json
from unittest.mock import MagicMock

from botocore.exceptions import ClientError

from features import resume_analysis


USER_ID = "user-123"
REQUEST_ID = "request-123"


def make_event() -> dict:
    return {
        "routeKey": "DELETE /analyses",
        "requestContext": {
            "requestId": REQUEST_ID,
            "routeKey": "DELETE /analyses",
            "http": {
                "method": "DELETE",
                "path": "/analyses",
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


def service_failure() -> ClientError:
    return ClientError(
        {
            "Error": {
                "Code": "InternalServerError",
                "Message": "Service failure",
            }
        },
        "DeleteItem",
    )


def test_bulk_delete_analyses_returns_counts(
    monkeypatch,
):
    table = MagicMock()

    table.query.return_value = {
        "Items": [
            {
                "pk": f"USER#{USER_ID}",
                "sk": "RESUME#analysis-1",
                "recordType": "resumeAnalysis",
                "userId": USER_ID,
                "analysisId": "analysis-1",
                "version": 2,
            },
            {
                "pk": f"USER#{USER_ID}",
                "sk": "RESUME#analysis-2",
                "recordType": "resumeAnalysis",
                "userId": USER_ID,
                "analysisId": "analysis-2",
                "version": 3,
            },
            {
                "pk": f"USER#{USER_ID}",
                "sk": "RESUME#analysis-3",
                "recordType": "resumeAnalysis",
                "userId": USER_ID,
                "analysisId": "analysis-3",
                "version": 1,
            },
        ]
    }

    table.delete_item.side_effect = [
        {},
        conditional_failure(),
        service_failure(),
    ]

    monkeypatch.setattr(
        resume_analysis,
        "table",
        table,
    )

    response = resume_analysis.delete_all_analyses(
        make_event()
    )
    body = response_body(response)

    assert response["statusCode"] == 200
    assert body == {
        "requested": 3,
        "deleted": 1,
        "conflicted": 1,
        "failed": 1,
        "recordType": "resumeAnalysis",
    }

    assert table.delete_item.call_count == 3


def test_bulk_delete_analyses_supports_legacy_version_zero(
    monkeypatch,
):
    table = MagicMock()

    table.query.return_value = {
        "Items": [
            {
                "pk": f"USER#{USER_ID}",
                "sk": "RESUME#legacy",
                "recordType": "resumeAnalysis",
                "userId": USER_ID,
                "analysisId": "legacy",
            }
        ]
    }

    monkeypatch.setattr(
        resume_analysis,
        "table",
        table,
    )

    response = resume_analysis.delete_all_analyses(
        make_event()
    )

    assert response["statusCode"] == 200

    call = table.delete_item.call_args.kwargs

    assert (
        call["ExpressionAttributeValues"][
            ":expectedVersion"
        ]
        == 0
    )


def test_bulk_delete_empty_analysis_list(
    monkeypatch,
):
    table = MagicMock()
    table.query.return_value = {"Items": []}

    monkeypatch.setattr(
        resume_analysis,
        "table",
        table,
    )

    response = resume_analysis.delete_all_analyses(
        make_event()
    )

    assert response_body(response) == {
        "requested": 0,
        "deleted": 0,
        "conflicted": 0,
        "failed": 0,
        "recordType": "resumeAnalysis",
    }

    table.delete_item.assert_not_called()
