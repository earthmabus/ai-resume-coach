# MS-006: Cross-Region Transport Starts at the Outbox Boundary

## Status

Accepted

## Decision

Introduce the first cross-region delivery transport at the transactional outbox
publisher boundary.

When placement is local, the outbox publisher continues to send to the local
regional `processing_queue`. When placement is non-local, the publisher makes
one SQS `SendMessage` attempt to the owning region's configured
`processing_queue`.

The transport contract is domain-neutral. It accepts a regional delivery
request containing the current region, owner region, delivery type, request
identifier, optional correlation identifier, and serialized message payload. It
does not know about resumes, job matching, tailoring, users, or domain
entities.

## Rationale

MR-009A1 and MR-009A2 established runtime identity, work ownership, placement,
and routing decisions without transport actions. The smallest shared boundary
for asynchronous regional delivery is the outbox publisher because it already
serializes durable work records into the shared processing contract.

Placing transport here avoids duplicating delivery logic in API handlers,
workers, or product feature modules, and preserves the existing separation:

```text
Runtime Identity
  -> Ownership
  -> Placement
  -> Transport
  -> Delivery
```

## Consequences

- API and worker handlers still do not act on non-local placement.
- The outbox publisher is the only runtime path that can deliver non-local
  asynchronous work in this slice.
- Regional delivery uses existing SQS queues; no new AWS service is introduced.
- The publisher resolves target queue URLs from configured queue names, caches
  each resolved URL for the warm process, and sends one message to the owner
  region.
- A failed regional delivery is reported back to the existing outbox publisher
  failure path.
- Existing outbox retry bookkeeping remains unchanged, but the transport itself
  does not implement retry, backoff, recovery, or failover.
- Local placement behavior remains backward compatible.
- Delivery remains at least once. If SQS accepts a message but the Lambda
  crashes or times out before the outbox item is marked delivered, a later
  publisher invocation can deliver the same outbox event again.
- Regional transport assumes both active processing queues are in the same AWS
  account as the publisher. Cross-account transport is out of scope.

## Non-Goals

This decision does not implement:

- cross-region HTTP forwarding
- Lambda-to-Lambda regional invocation
- failover
- health-based routing
- Route 53 or CloudFront changes
- transport retry or backoff
- queue draining
- message replay
- distributed transactions
