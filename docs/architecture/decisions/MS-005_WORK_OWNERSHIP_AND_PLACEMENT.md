# MS-005: Work Ownership and Placement Are Transport-Neutral

## Status

Accepted

## Decision

Represent work ownership separately from runtime identity and transport
actions.

Runtime identity describes where code is running. Work ownership describes
which configured region owns a unit of work. Placement evaluation compares
those facts and returns a pure result:

- local
- non-local
- invalid
- unresolved

HTTP, SQS, scheduled jobs, replay tools, and future transports may consume the
same placement result, but this decision does not introduce transport actions.

## Rationale

Active-active operation needs a stable answer to:

```text
Which region owns this unit of work?
Is this runtime executing in that region?
```

Those questions must be answerable before introducing forwarding, failover, or
regional delivery behavior. Keeping the ownership and placement layers
transport-neutral avoids coupling regional policy to API Gateway, Lambda event
formats, SQS records, or future execution paths.

## Consequences

- Newly created idempotency and asynchronous outbox work records include
  `ownerRegion`.
- Outbox payloads and SQS serialization preserve `ownerRegion` when present.
- Legacy records without `ownerRegion` remain readable; the ownership resolver
  can explicitly treat missing ownership as local legacy work.
- Invalid owner regions are reported as invalid rather than silently becoming
  local work.
- Non-local placement is a diagnostic fact, not a forwarding instruction.
- No handler may reject, redirect, invoke another region, or requeue work based
  on placement until a later decision explicitly introduces transport actions.

## Non-Goals

This decision does not implement:

- cross-region HTTP forwarding
- cross-region Lambda invocation
- cross-region SQS publishing
- failover behavior
- traffic weighting
- user or tenant regional affinity
- data migration or ownership backfill
