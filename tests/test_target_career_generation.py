import json
from unittest.mock import MagicMock

from features import target_career_generation


def event(route_key, body=None, generation_id=None):
    value = {
        "requestContext": {
            "http": {"method": route_key.split()[0], "path": "/target-careers"},
            "requestId": "request-1",
            "authorizer": {"jwt": {"claims": {"sub": "user-1"}}},
        },
        "headers": {"x-correlation-id": "correlation-1"},
        "pathParameters": {"id": generation_id} if generation_id else {},
    }
    if body is not None:
        value["body"] = json.dumps(body)
    return value


def test_generation_submission_persists_and_queues(monkeypatch):
    table = MagicMock()
    sqs = MagicMock()
    monkeypatch.setattr(target_career_generation, "table", table)
    monkeypatch.setattr(target_career_generation, "sqs", sqs)
    monkeypatch.setattr(target_career_generation, "queue_url", "queue-url")
    monkeypatch.setattr(target_career_generation.uuid, "uuid4", lambda: "generation-1")

    response = target_career_generation.generate_target_career_details(event(
        "POST /target-careers/generate-details",
        {"roleTitle": "Director of Software Engineering", "industry": "Technology"},
    ))

    assert response["statusCode"] == 202
    table.put_item.assert_called_once()
    queued = json.loads(sqs.send_message.call_args.kwargs["MessageBody"])
    assert queued["jobType"] == "targetCareerGeneration"
    assert queued["generationId"] == "generation-1"


def test_generation_requires_role_title(monkeypatch):
    monkeypatch.setattr(target_career_generation, "queue_url", "queue-url")
    response = target_career_generation.generate_target_career_details(event(
        "POST /target-careers/generate-details", {"industry": "Technology"}
    ))
    assert response["statusCode"] == 400


def test_generation_status_is_scoped_to_user(monkeypatch):
    table = MagicMock()
    table.get_item.return_value = {"Item": {
        "userId": "user-1", "status": "completed", "generationId": "generation-1",
        "keyResponsibilities": "Lead teams",
    }}
    monkeypatch.setattr(target_career_generation, "table", table)
    response = target_career_generation.get_target_career_generation(event(
        "GET /target-careers/generations/{id}", generation_id="generation-1"
    ))
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["keyResponsibilities"] == "Lead teams"
