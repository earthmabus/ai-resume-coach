from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from core.workflow_state import (
    STATUS_QUEUED,
    STATUS_QUEUED_PENDING_DISPATCH,
    assert_transition,
)
from core.dynamodb_contract import (
    GSI2_INDEX_NAME,
    GSI2_PARTITION_KEY,
    GSI2_SORT_KEY,
)

DISPATCH_PENDING = "PENDING"
DISPATCH_CLAIMED = "CLAIMED"
DISPATCH_DISPATCHED = "DISPATCHED"
STATUS_PENDING_DISPATCH = STATUS_QUEUED_PENDING_DISPATCH
DEFAULT_LEASE_SECONDS = 300
DEFAULT_BATCH_SIZE = 25
MAX_RETRY_DELAY_SECONDS = 1800


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def dispatch_partition(owner_region: str, status: str = DISPATCH_PENDING) -> str:
    return f"WORKFLOW_DISPATCH#{owner_region}#{status}"


def dispatch_sort_key(next_attempt_at: str, analysis_id: str) -> str:
    return f"{next_attempt_at}#{analysis_id}"


def retry_delay_seconds(attempt: int) -> int:
    return min(60 * (2 ** max(0, attempt - 1)), MAX_RETRY_DELAY_SECONDS)


def is_conditional_failure(error: ClientError) -> bool:
    return (
        error.response.get("Error", {}).get("Code")
        == "ConditionalCheckFailedException"
    )


@dataclass(frozen=True)
class WorkflowDispatchResult:
    examined: int = 0
    claimed: int = 0
    dispatched: int = 0
    failed: int = 0
    skipped: int = 0
    recovered: int = 0
    recovery_skipped: int = 0


class ResumeWorkflowDispatcher:
    def __init__(
        self,
        *,
        table: Any,
        sqs_client: Any,
        queue_url: str,
        region: str,
        deployment_id: str,
        batch_size: int = DEFAULT_BATCH_SIZE,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
    ) -> None:
        self.table = table
        self.sqs_client = sqs_client
        self.queue_url = queue_url
        self.region = region
        self.deployment_id = deployment_id
        self.batch_size = batch_size
        self.lease_seconds = lease_seconds

    def find_pending(self, now: str | None = None) -> list[dict[str, Any]]:
        current = now or utc_now()
        response = self.table.query(
            IndexName=GSI2_INDEX_NAME,
            KeyConditionExpression=(
                Key(GSI2_PARTITION_KEY).eq(dispatch_partition(self.region))
                & Key(GSI2_SORT_KEY).lte(f"{current}#\uffff")
            ),
            Limit=self.batch_size,
        )
        return list(response.get("Items", []))

    def claim(self, item: dict[str, Any]) -> tuple[dict[str, Any], str] | None:
        attempt_id = str(uuid.uuid4())
        now_epoch = int(time.time())
        lease_expires = now_epoch + self.lease_seconds
        attempts = int(item.get("dispatchAttempts", 0)) + 1

        try:
            response = self.table.update_item(
                Key={"pk": item["pk"], "sk": item["sk"]},
                UpdateExpression=(
                    "SET dispatchStatus = :claimed, "
                    "dispatchAttemptId = :attemptId, "
                    "dispatchLeaseExpiresAt = :leaseExpiresAt, "
                    "dispatchAttempts = :attempts, "
                    "updatedAt = :updatedAt, "
                    "lastUpdatedRegion = :region, "
                    "lastUpdatedByDeploymentId = :deploymentId, "
                    "gsi2pk = :claimedPartition, "
                    "gsi2sk = :claimedSortKey"
                ),
                ConditionExpression=(
                    "dispatchStatus = :pending "
                    "AND ownerRegion = :region "
                    "AND #status = :pendingStatus"
                ),
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":claimed": DISPATCH_CLAIMED,
                    ":pending": DISPATCH_PENDING,
                    ":attemptId": attempt_id,
                    ":leaseExpiresAt": lease_expires,
                    ":attempts": attempts,
                    ":updatedAt": utc_now(),
                    ":region": self.region,
                    ":deploymentId": self.deployment_id,
                    ":pendingStatus": STATUS_PENDING_DISPATCH,
                    ":claimedPartition": dispatch_partition(self.region, DISPATCH_CLAIMED),
                    ":claimedSortKey": dispatch_sort_key(datetime.fromtimestamp(lease_expires, tz=timezone.utc).isoformat(), str(item["analysisId"])),
                },
                ReturnValues="ALL_NEW",
            )
            return response["Attributes"], attempt_id
        except ClientError as error:
            if is_conditional_failure(error):
                return None
            raise


    def find_expired_claims(self, now: str | None = None) -> list[dict[str, Any]]:
        current = now or utc_now()
        response = self.table.query(
            IndexName=GSI2_INDEX_NAME,
            KeyConditionExpression=(
                Key(GSI2_PARTITION_KEY).eq(
                    dispatch_partition(self.region, DISPATCH_CLAIMED)
                )
                & Key(GSI2_SORT_KEY).lte(f"{current}#\uffff")
            ),
            Limit=self.batch_size,
        )
        return list(response.get("Items", []))

    def recover_expired_claim(self, item: dict[str, Any]) -> bool:
        attempt_id = str(item.get("dispatchAttemptId") or "")
        if not attempt_id:
            return False

        now = utc_now()
        analysis_id = str(item["analysisId"])
        try:
            self.table.update_item(
                Key={"pk": item["pk"], "sk": item["sk"]},
                UpdateExpression=(
                    "SET dispatchStatus = :pending, "
                    "nextDispatchAttemptAt = :nextAttemptAt, "
                    "gsi2pk = :pendingPartition, "
                    "gsi2sk = :pendingSortKey, "
                    "updatedAt = :updatedAt, "
                    "lastUpdatedRegion = :region, "
                    "lastUpdatedByDeploymentId = :deploymentId "
                    "REMOVE dispatchLeaseExpiresAt"
                ),
                ConditionExpression=(
                    "dispatchStatus = :claimed "
                    "AND dispatchAttemptId = :attemptId "
                    "AND ownerRegion = :region "
                    "AND dispatchLeaseExpiresAt <= :nowEpoch"
                ),
                ExpressionAttributeValues={
                    ":pending": DISPATCH_PENDING,
                    ":claimed": DISPATCH_CLAIMED,
                    ":attemptId": attempt_id,
                    ":nextAttemptAt": now,
                    ":pendingPartition": dispatch_partition(self.region),
                    ":pendingSortKey": dispatch_sort_key(now, analysis_id),
                    ":updatedAt": now,
                    ":region": self.region,
                    ":deploymentId": self.deployment_id,
                    ":nowEpoch": int(time.time()),
                },
            )
            return True
        except ClientError as error:
            if is_conditional_failure(error):
                return False
            raise

    def recover_expired_claims(self) -> tuple[int, int]:
        recovered = skipped = 0
        for candidate in self.find_expired_claims():
            if self.recover_expired_claim(candidate):
                recovered += 1
            else:
                skipped += 1
        return recovered, skipped

    @staticmethod
    def message_for(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "jobType": "resumeAnalysis",
            "eventType": "ResumeAnalysisRequested",
            "analysisId": item["analysisId"],
            "userId": item["userId"],
            "requestId": item.get("createdByRequestId", ""),
            "createdByRequestId": item.get("createdByRequestId", ""),
            "correlationId": item.get("correlationId", ""),
            "ownerRegion": item.get("ownerRegion", ""),
            "sourceRegion": item.get("createdRegion", ""),
            "documentBucket": item.get("documentBucket", ""),
            "documentKey": item.get("documentKey", ""),
            "fileName": item.get("fileName", ""),
            "requestedProvider": item.get("requestedProvider", ""),
        }

    def mark_dispatched(self, item: dict[str, Any], attempt_id: str) -> None:
        assert_transition(str(item.get("status") or ""), STATUS_QUEUED)
        self.table.update_item(
            Key={"pk": item["pk"], "sk": item["sk"]},
            UpdateExpression=(
                "SET dispatchStatus = :dispatched, #status = :queued, "
                "dispatchedAt = :dispatchedAt, updatedAt = :updatedAt, "
                "lastUpdatedRegion = :region, "
                "lastUpdatedByDeploymentId = :deploymentId "
                "REMOVE dispatchLeaseExpiresAt"
            ),
            ConditionExpression=(
                "dispatchStatus = :claimed "
                "AND dispatchAttemptId = :attemptId "
                "AND ownerRegion = :region "
                "AND #status = :pendingStatus"
            ),
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":dispatched": DISPATCH_DISPATCHED,
                ":queued": STATUS_QUEUED,
                ":claimed": DISPATCH_CLAIMED,
                ":attemptId": attempt_id,
                ":dispatchedAt": utc_now(),
                ":updatedAt": utc_now(),
                ":region": self.region,
                ":deploymentId": self.deployment_id,
                ":pendingStatus": STATUS_PENDING_DISPATCH,
            },
        )

    def release_for_retry(self, item: dict[str, Any], attempt_id: str) -> None:
        attempt = int(item.get("dispatchAttempts", 1))
        next_epoch = int(time.time()) + retry_delay_seconds(attempt)
        next_attempt_at = datetime.fromtimestamp(
            next_epoch, tz=timezone.utc
        ).isoformat()
        analysis_id = str(item["analysisId"])

        self.table.update_item(
            Key={"pk": item["pk"], "sk": item["sk"]},
            UpdateExpression=(
                "SET dispatchStatus = :pending, "
                "nextDispatchAttemptAt = :nextAttemptAt, "
                "gsi2pk = :gsi2pk, gsi2sk = :gsi2sk, "
                "updatedAt = :updatedAt, "
                "lastUpdatedRegion = :region, "
                "lastUpdatedByDeploymentId = :deploymentId "
                "REMOVE dispatchLeaseExpiresAt"
            ),
            ConditionExpression=(
                "dispatchStatus = :claimed "
                "AND dispatchAttemptId = :attemptId "
                "AND ownerRegion = :region"
            ),
            ExpressionAttributeValues={
                ":pending": DISPATCH_PENDING,
                ":claimed": DISPATCH_CLAIMED,
                ":attemptId": attempt_id,
                ":nextAttemptAt": next_attempt_at,
                ":gsi2pk": dispatch_partition(self.region),
                ":gsi2sk": dispatch_sort_key(next_attempt_at, analysis_id),
                ":updatedAt": utc_now(),
                ":region": self.region,
                ":deploymentId": self.deployment_id,
            },
        )

    def dispatch_pending(self) -> WorkflowDispatchResult:
        recovered, recovery_skipped = self.recover_expired_claims()
        examined = claimed = dispatched = failed = skipped = 0
        for candidate in self.find_pending():
            examined += 1
            claim = self.claim(candidate)
            if claim is None:
                skipped += 1
                continue
            claimed_item, attempt_id = claim
            claimed += 1
            try:
                self.sqs_client.send_message(
                    QueueUrl=self.queue_url,
                    MessageBody=json.dumps(
                        self.message_for(claimed_item),
                        separators=(",", ":"),
                    ),
                )
                self.mark_dispatched(claimed_item, attempt_id)
                dispatched += 1
            except Exception:
                failed += 1
                self.release_for_retry(claimed_item, attempt_id)

        return WorkflowDispatchResult(
            examined=examined,
            claimed=claimed,
            dispatched=dispatched,
            failed=failed,
            skipped=skipped,
            recovered=recovered,
            recovery_skipped=recovery_skipped,
        )
