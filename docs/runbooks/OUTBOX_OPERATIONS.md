# Transactional Outbox Operations

## Lifecycle

`PENDING → DISPATCHING → DELIVERED`

A delivery failure below the configured attempt limit becomes `FAILED_RETRYABLE` and receives `nextDeliveryAttemptAt`. A failure at the limit becomes `FAILED_PERMANENT`, leaves the dispatch GSI, and requires operator replay.

Delivered events receive an `expiresAt` timestamp and are removed automatically by DynamoDB TTL after the configured retention period. TTL deletion is asynchronous and may occur after the timestamp.

## Defaults

- Batch size: 25
- Parallel workers: 4
- Maximum delivery attempts: 20
- Delivered retention: 30 days
- Maximum retry backoff: 30 minutes

## Investigate permanent failures

```bash
aws dynamodb scan \
  --table-name ai-resume-coach-dev-resume-analysis \
  --filter-expression "#s = :status" \
  --expression-attribute-names '{"#s":"status"}' \
  --expression-attribute-values '{":status":{"S":"FAILED_PERMANENT"}}'
```

Review `eventId`, `eventType`, `aggregateId`, `deliveryAttempts`, `lastDeliveryError`, and `permanentlyFailedAt`. Do not print or copy the full payload unless it is necessary and authorized because it may contain user data.

## Investigate regional delivery

The outbox publisher emits one structured diagnostic record for each placement
decision it acts on. Search by `outboxEventId`, `requestId`, or
`correlationId` and review:

- `currentRegion`
- `ownerRegion`
- `placementAction`
- `deliveryType`
- `deliveryStatus`
- `transportMessageId`
- `deliveryReason`
- `deliveryAttempts`

`deliveryMessageId` may appear as a compatibility alias for
`transportMessageId` in older delivery diagnostics.

`NON_LOCAL_REGION` with `DELIVERED` means SQS accepted the message in the owner
region. `DELIVERY_FAILED`, `UNSUPPORTED_REGION`, or `INVALID_PLACEMENT` means
the outbox publisher left the item recoverable through the existing retry or
permanent-failure path.

Regional delivery is at least once. If SQS accepts a message and the publisher
crashes before marking the outbox item `DELIVERED`, a later invocation can send
the same `outboxEventId` again. Do not manually delete the outbox item to hide a
duplicate; investigate downstream idempotency and the final business state.

## Trace one unit of work

Use structured logs before reading payload-bearing DynamoDB attributes. Start
with the identifier you have:

- `requestId`: search API logs, idempotency records, outbox publisher
  diagnostics, and worker diagnostics. The matching outbox log gives
  `outboxEventId`; the matching worker log gives `workId` and
  `transportMessageId`.
- `correlationId`: search API, outbox publisher, regional transport, and worker
  logs to group related retries or continuations. If no explicit correlation ID
  exists on legacy records, use `requestId`.
- `workId`: inspect the typed work record by its base key or entity GSI, then
  use `createdByRequestId`, `correlationId`, `ownerRegion`, `createdRegion`,
  and status fields to continue the investigation.
- `outboxEventId`: inspect the outbox record status, `deliveryAttempts`,
  `createdByRequestId`, `correlationId`, `ownerRegion`, `createdRegion`,
  `transportMessageId`, and the latest delivery error fields.
- `transportMessageId`: search worker logs for `transportMessageId`. SQS
  message IDs are delivery evidence only and are not durable logical work IDs.

Expected stops:

- API accepted but no work exists: start with `requestId` and check the
  idempotency record and API error logs.
- Work exists but no outbox event exists: use `workId` and
  `createdByRequestId` to verify whether the transaction completed or failed.
- Outbox is `PENDING` or `FAILED_RETRYABLE`: the outbox remains the durable
  recovery boundary and should be retried by the existing publisher schedule.
- SQS accepted but the worker did not complete: use `transportMessageId`,
  `outboxEventId`, and `workId` in worker logs and final work status.
- Duplicate worker execution: compare `workId`, `outboxEventId`,
  `processingAttemptId`, and final status. At-least-once delivery is expected.

## Replay one event

Replay does not send directly to SQS. It conditionally moves a terminal event back to `PENDING`, resets `deliveryAttempts`, restores the GSI fields, and lets the scheduled publisher dispatch it.

```bash
python tools/replay_outbox.py \
  --event-id EVENT_ID \
  --table-name ai-resume-coach-dev-resume-analysis \
  --region us-east-1 \
  --operator "$USER"
```

Then confirm the publisher handles the event and the business workflow completes.

## Alarm response

`outbox-permanent-failures` means at least one event became terminal during the alarm period. Investigate before replaying. Replaying without correcting the underlying cause will cause the event to fail again.

## Safety

- Replay only `FAILED_PERMANENT` records.
- Never edit an outbox item manually in the console.
- Never send its payload directly to SQS.
- Record the incident and reason for replay.
- Confirm the downstream worker remains idempotent.
