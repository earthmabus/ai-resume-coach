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
