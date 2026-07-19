import json
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from core.workflow_dispatch import (
    DISPATCH_CLAIMED,
    ResumeWorkflowDispatcher,
    dispatch_partition,
    dispatch_sort_key,
)


class FakeTable:
    def __init__(self, pending=None, expired=None, conditional_fail=False):
        self.pending = list(pending or [])
        self.expired = list(expired or [])
        self.conditional_fail = conditional_fail
        self.updates = []
        self.query_count = 0

    def query(self, **kwargs):
        self.query_count += 1
        return {"Items": list(self.expired if self.query_count == 1 else self.pending)}

    def update_item(self, **kwargs):
        self.updates.append(kwargs)
        if self.conditional_fail:
            raise ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException", "Message": "race"}},
                "UpdateItem",
            )
        values = kwargs.get("ExpressionAttributeValues", {})
        if all(name in values for name in (":claimed", ":attemptId", ":attempts")):
            item = dict(self.pending[0])
            item["dispatchStatus"] = "CLAIMED"
            item["dispatchAttemptId"] = values[":attemptId"]
            item["dispatchAttempts"] = values[":attempts"]
            item["gsi2pk"] = values[":claimedPartition"]
            item["gsi2sk"] = values[":claimedSortKey"]
            return {"Attributes": item}
        return {"Attributes": {}}


class FakeSqs:
    def __init__(self, fail=False):
        self.fail = fail
        self.messages = []

    def send_message(self, **kwargs):
        if self.fail:
            raise RuntimeError("send failed")
        self.messages.append(kwargs)
        return {"MessageId": "message-1"}


def pending_item():
    return {
        "pk": "USER#u1", "sk": "RESUME#a1", "analysisId": "a1", "userId": "u1",
        "status": "QUEUED_PENDING_DISPATCH", "dispatchStatus": "PENDING",
        "dispatchAttempts": 0, "ownerRegion": "us-east-1", "createdRegion": "us-west-2",
        "createdByRequestId": "r1", "correlationId": "c1",
    }


def expired_item():
    return {
        **pending_item(),
        "dispatchStatus": "CLAIMED",
        "dispatchAttemptId": "attempt-old",
        "dispatchLeaseExpiresAt": 1,
        "gsi2pk": dispatch_partition("us-east-1", DISPATCH_CLAIMED),
        "gsi2sk": dispatch_sort_key("2020-01-01T00:00:00+00:00", "a1"),
    }


def dispatcher(table, sqs=None):
    return ResumeWorkflowDispatcher(
        table=table, sqs_client=sqs or FakeSqs(), queue_url="queue-url",
        region="us-east-1", deployment_id="deploy-1",
    )


def test_dispatch_keys_are_deterministic():
    assert dispatch_partition("us-east-1") == "WORKFLOW_DISPATCH#us-east-1#PENDING"
    assert dispatch_partition("us-east-1", "CLAIMED") == "WORKFLOW_DISPATCH#us-east-1#CLAIMED"
    assert dispatch_sort_key("2026-01-01T00:00:00+00:00", "a1") == "2026-01-01T00:00:00+00:00#a1"


def test_pending_analysis_is_claimed_sent_and_marked_dispatched():
    table = FakeTable(pending=[pending_item()])
    sqs = FakeSqs()
    result = dispatcher(table, sqs).dispatch_pending()
    assert (result.examined, result.claimed, result.dispatched, result.failed) == (1, 1, 1, 0)
    assert result.recovered == 0
    assert json.loads(sqs.messages[0]["MessageBody"])["analysisId"] == "a1"
    claim_values = table.updates[0]["ExpressionAttributeValues"]
    assert claim_values[":claimedPartition"] == dispatch_partition("us-east-1", "CLAIMED")


def test_failed_send_releases_analysis_for_retry():
    table = FakeTable(pending=[pending_item()])
    result = dispatcher(table, FakeSqs(fail=True)).dispatch_pending()
    assert (result.claimed, result.dispatched, result.failed) == (1, 0, 1)
    values = table.updates[-1]["ExpressionAttributeValues"]
    assert values[":pending"] == "PENDING"
    assert values[":gsi2pk"] == dispatch_partition("us-east-1")


def test_expired_claim_is_recovered_before_dispatch_query():
    table = FakeTable(expired=[expired_item()])
    result = dispatcher(table).dispatch_pending()
    assert result.recovered == 1
    assert result.recovery_skipped == 0
    recovery = table.updates[0]
    values = recovery["ExpressionAttributeValues"]
    assert values[":pendingPartition"] == dispatch_partition("us-east-1")
    assert values[":attemptId"] == "attempt-old"
    assert "dispatchLeaseExpiresAt <= :nowEpoch" in recovery["ConditionExpression"]


def test_recovery_race_is_safely_skipped():
    table = FakeTable(expired=[expired_item()], conditional_fail=True)
    result = dispatcher(table).dispatch_pending()
    assert result.recovered == 0
    assert result.recovery_skipped == 1
