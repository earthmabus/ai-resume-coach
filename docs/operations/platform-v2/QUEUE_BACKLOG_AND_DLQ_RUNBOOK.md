# Queue Backlog and DLQ Runbook

## Detect and preserve evidence

Record UTC time, deployment ID, queue and DLQ attributes, event-source mapping
state, worker alarms, sanitized publisher logs, sanitized worker logs, and safe
correlation/work/outbox identifiers.

## Backlog response

1. Keep the healthy peer and DynamoDB table unchanged.
2. Confirm the owning-region worker mapping is enabled.
3. Review throttles, errors, concurrency, and configuration.
4. Correct or roll back the owning-region worker.
5. Observe visible-message count and oldest-message age decline.
6. Verify completed state and duplicate-delivery safety.

Do not copy messages to the peer queue or rewrite ownership.

## DLQ response

1. Inspect only a bounded, sanitized sample.
2. Classify the cause.
3. Correct the cause before replay.
4. Use repository replay tooling only for an individually approved event.
5. Confirm logical work identity is preserved.
6. Verify queue and DLQ depth return to normal.
