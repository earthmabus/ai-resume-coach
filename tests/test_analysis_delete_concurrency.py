from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from core.errors import ResourceConflictError
from features import resume_analysis


USER_ID = "user-123"
ANALYSIS_ID = "analysis-123"
REQUEST_ID = "request-123"


def make_event(
    *,
    version: str | None = "3",
) -> dict:
    query_parameters = {}

    if version is not None:
        query_parameters["version"] = version

    return {
        "routeKey": "DELETE /analysis/{id}",
        "pathParameters": {
            "id": ANALYSIS_ID,
        },
        "queryStringParameters": query_parameters,
        "requestContext": {
            "requestId": REQUEST_ID,
            "routeKey": "DELETE /analysis/{id}",
            "http": {
                "method": "DELETE",
                "path": f"/analysis/{ANALYSIS_ID}",
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


def test_delete_analysis_requires_version(monkeypatch):
    table = MagicMock()
    monkeypatch.setattr(resume_analysis, "table", table)

    response = resume_analysis.delete_analysis(
        make_event(version=None)
    )

    assert response["statusCode"] == 400
    assert "version query parameter is required" in (
        response_body(response)["error"]
    )

    table.get_item.assert_not_called()
    table.delete_item.assert_not_called()


def test_delete_analysis_uses_direct_base_key(
    monkeypatch,
):
    table = MagicMock()
    table.get_item.return_value = {
        "Item": {
            "pk": f"USER#{USER_ID}",
            "sk": f"RESUME#{ANALYSIS_ID}",
            "recordType": "resumeAnalysis",
            "userId": USER_ID,
            "analysisId": ANALYSIS_ID,
            "version": 3,
        }
    }

    monkeypatch.setattr(resume_analysis, "table", table)

    response = resume_analysis.delete_analysis(
        make_event(version="3")
    )

    assert response["statusCode"] == 200

    table.get_item.assert_called_once_with(
        Key={
            "pk": f"USER#{USER_ID}",
            "sk": f"RESUME#{ANALYSIS_ID}",
        },
        ConsistentRead=True,
    )

    call = table.delete_item.call_args.kwargs

    assert call["Key"] == {
        "pk": f"USER#{USER_ID}",
        "sk": f"RESUME#{ANALYSIS_ID}",
    }
    assert (
        call["ExpressionAttributeValues"][
            ":expectedVersion"
        ]
        == 3
    )


def test_delete_missing_analysis_returns_404(
    monkeypatch,
):
    table = MagicMock()
    table.get_item.return_value = {}

    monkeypatch.setattr(resume_analysis, "table", table)

    response = resume_analysis.delete_analysis(
        make_event(version="3")
    )

    assert response["statusCode"] == 404
    table.delete_item.assert_not_called()


def test_stale_analysis_delete_raises_conflict(
    monkeypatch,
):
    table = MagicMock()
    table.get_item.return_value = {
        "Item": {
            "userId": USER_ID,
            "version": 4,
        }
    }
    table.delete_item.side_effect = conditional_failure()

    monkeypatch.setattr(resume_analysis, "table", table)

    with pytest.raises(ResourceConflictError):
        resume_analysis.delete_analysis(
            make_event(version="3")
        )


def test_unversioned_legacy_analysis_accepts_zero(
    monkeypatch,
):
    table = MagicMock()
    table.get_item.return_value = {
        "Item": {
            "userId": USER_ID,
            "recordType": "resumeAnalysis",
        }
    }

    monkeypatch.setattr(resume_analysis, "table", table)

    response = resume_analysis.delete_analysis(
        make_event(version="0")
    )

    assert response["statusCode"] == 200

    call = table.delete_item.call_args.kwargs

    assert (
        call["ExpressionAttributeValues"][
            ":expectedVersion"
        ]
        == 0
    )
