# Processing Architecture

Shared processing queue, worker model, retries, DLQ, and rationale.

## Owner Region Metadata

The shared processing queue remains a regional platform capability named
`processing_queue` with a corresponding `processing_dlq`.

New outbox records include `ownerRegion` alongside existing creation metadata
such as `createdRegion` and `createdByRequestId`. The outbox payload also
includes `ownerRegion`, and the outbox publisher preserves it when serializing
the SQS message.

`sourceRegion` remains for compatibility and continues to describe where the
work was submitted. `ownerRegion` describes the region that owns execution of
the work.

Existing outbox records and SQS messages without `ownerRegion` remain
compatible with workers. Missing ownership is handled by the transport-neutral
ownership resolver rather than by changing worker behavior.

## Transport Boundaries

The transactional outbox publisher is the first cross-region transport
boundary. It evaluates placement for each claimed outbox item before publishing
the processing message.

When placement is local, the publisher sends the existing serialized message to
the local regional `processing_queue`.

When placement is non-local, the publisher resolves the owning region's
configured `processing_queue` URL, caches that resolved URL for the warm
process, and makes one SQS delivery attempt. The transport request contains
only regional delivery metadata and the already serialized processing payload;
it does not depend on resume analysis, job matching, tailoring, API Gateway, or
SQS event structures.

Delivery is at least once. If SQS accepts a message but the publisher crashes,
times out, or loses its DynamoDB update before marking the outbox item
`DELIVERED`, the outbox lease can expire and a later publisher invocation can
send the same `outboxEventId` again. Downstream workers must continue to treat
`outboxEventId`, `requestId`, deterministic work IDs, and existing idempotency
records as duplicate-protection inputs.

The publisher emits structured, payload-safe regional-delivery diagnostics with
the outbox event ID, request ID, correlation ID when present, current region,
owner region, placement action, delivery type, delivery status, delivery
message ID when available, failure reason, and existing delivery-attempt count.

Workers and API handlers do not act on non-local placement. No HTTP request is
redirected, no Lambda is invoked across regions, and no worker requeues,
rejects, deletes, or forwards a message because of placement. Failover,
transport retry, replay, queue draining, and health-based routing remain
reserved for later multi-site slices.

## Correlation Contract

Processing messages use one schema for local and cross-region delivery. The
shared diagnostic contract is:

- `requestId`: originating API command identifier
- `correlationId`: operational grouping identifier, falling back to `requestId`
  for legacy-compatible messages
- `jobId` plus the typed work ID field such as `analysisId`, `matchId`,
  `tailoringId`, or `interviewPrepId`
- `outboxEventId`: durable outbox event identity when the message came from the
  transactional outbox
- `eventType`
- `ownerRegion`
- `sourceRegion`
- `sourceDeploymentId`

Workers normalize these fields at the shared SQS processing boundary and emit
payload-safe structured diagnostics with SQS `messageId` as
`transportMessageId` and Lambda request ID as `runtimeInvocationId`. Those
runtime identifiers are evidence for one delivery or invocation; they are not
persisted as logical request identity.

`transportMessageId` and `runtimeInvocationId` are the canonical correlation
field names. `deliveryMessageId` and `awsRequestId` may still appear in logs as
compatibility aliases where older diagnostics already used those names.

High-cardinality identifiers belong in structured logs, not metric dimensions.
Worker failure metrics continue to use low-cardinality dimensions only.
