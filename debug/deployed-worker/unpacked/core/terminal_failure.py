from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TerminalFailureEnvelope:
    failure_id: str
    work_id: str
    job_type: str
    record_type: str
    status: str
    failure_category: str
    processing_attempt: int
    max_processing_attempts: int
    error_type: str
    error_message: str
    request_id: str
    correlation_id: str
    outbox_event_id: str
    owner_region: str
    source_region: str
    failed_region: str
    deployment_id: str
    failed_at: str

    def as_message(self) -> dict[str, Any]:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "eventType": "WORKFLOW_TERMINAL_FAILURE",
            "failureId": self.failure_id,
            "workId": self.work_id,
            "jobType": self.job_type,
            "recordType": self.record_type,
            "status": self.status,
            "failureCategory": self.failure_category,
            "processingAttempt": self.processing_attempt,
            "maxProcessingAttempts": self.max_processing_attempts,
            "errorType": self.error_type,
            "errorMessage": self.error_message[:2000],
            "requestId": self.request_id,
            "correlationId": self.correlation_id,
            "outboxEventId": self.outbox_event_id,
            "ownerRegion": self.owner_region,
            "sourceRegion": self.source_region,
            "failedRegion": self.failed_region,
            "deploymentId": self.deployment_id,
            "failedAt": self.failed_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_message(), separators=(",", ":"), sort_keys=True)
