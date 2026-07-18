# MS-007: End-to-End Correlation Uses Explicit Logical and Operational Identifiers

## Status

Accepted

## Decision

The asynchronous multi-site lifecycle uses one explicit correlation vocabulary:

- `requestId`: the logical originating API command identifier. It is created
  from the API Gateway request ID and remains the stable request identity for
  idempotency records, work records, outbox records, and processing messages.
  Existing durable fields named `createdByRequestId` and `updatedByRequestId`
  describe creation and mutation provenance for that same request identity.
- `correlationId`: an operational grouping identifier. A validated
  `X-Correlation-Id` request header may supply it; otherwise it falls back to
  `requestId`. Invalid client-supplied values are ignored and do not affect
  public API behavior.
- `workId`: the durable business-work identifier, such as an analysis, job
  match, tailoring, or interview-preparation ID.
- `outboxEventId`: the immutable durable outbox event identifier.
- `transportMessageId`: provider evidence from SQS after delivery is accepted.
  It is diagnostic and not a logical work identifier. Existing delivery
  diagnostics may also expose `deliveryMessageId` as a compatibility alias.
- `runtimeInvocationId`: Lambda invocation evidence. It is diagnostic only and
  is not persisted as durable request identity. `awsRequestId` is retained only
  where existing logs already emitted the AWS name.

New idempotency, work, outbox, and processing-message contracts preserve
`requestId` and `correlationId` when available. Legacy compatible records and
messages without `correlationId` remain processable; diagnostic correlation
falls back to `requestId` rather than inventing historical values.

## Rationale

MR-009A1 through MR-009A3 established regional topology, ownership, placement,
and one cross-region SQS transport attempt. Operators now need to follow one
logical unit of work across API handling, idempotency, durable work creation,
the transactional outbox, local or cross-region SQS delivery, worker execution,
and final state transitions.

The identifiers above represent distinct concepts. Collapsing them would make
incident investigation ambiguous: an API request, durable work item, outbox
event, SQS message, and Lambda invocation can each fail or duplicate at
different boundaries.

## Consequences

- Request context owns correlation creation and validation.
- Idempotency records preserve the original correlation identifier during
  retries and continuation without changing idempotency conflict semantics.
- Work and outbox creation receive correlation metadata from the idempotency
  reservation when present, falling back to the request context for newly
  created work.
- Local and cross-region queue delivery use the same processing message
  correlation fields.
- Worker diagnostics normalize safe identifiers at the shared worker boundary
  so business features do not reconstruct logging context themselves.
- Structured logs may include high-cardinality identifiers, but metrics must
  not use request IDs, correlation IDs, work IDs, outbox event IDs, or SQS
  message IDs as CloudWatch metric dimensions.
- Sensitive payload content, resumes, job descriptions, tokens, and raw message
  bodies must not be logged.
- No distributed tracing service, transport retry, failover, replay, or owner
  reassignment is introduced by this decision.

## Non-Goals

This decision does not implement:

- AWS X-Ray or OpenTelemetry
- trace spans or sampling
- new queues or AWS services
- failover or owner reassignment
- transport-level retry
- replay or recovery tooling
- authorization based on correlation metadata
