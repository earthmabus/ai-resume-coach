# MR-012 Multi-Site Final Reconciliation

## Status

Implementation reconciliation complete. Runtime evidence remains pending until
MR-009D3B and MR-010 execution reports contain successful observations from the
authorized development environment.

## Current topology

- Active application regions: `us-east-1`, `us-west-2`.
- DynamoDB MRSC witness region: `us-east-2`.
- Each active region contains an HTTP API, API Lambda, outbox publisher, SQS
  processing queue, DLQ, and worker Lambda.
- Cognito identity and the DynamoDB system of record are shared capabilities.
- Optional Route 53 latency routing publishes only sites enabled through
  `site_routing_enabled`.

## Request and processing lifecycle

A protected request enters one regional HTTP API. The API derives runtime
identity, request ID, and correlation ID. Asynchronous work and an outbox record
are persisted atomically. The work record carries deterministic `ownerRegion`.
The scheduled publisher sends the event to the queue in that region. The worker
validates ownership and workflow state before processing.

Duplicate API, publisher, queue, and worker deliveries are controlled through
idempotency and conditional writes.

## Data architecture

The ResumeAnalysis table is the MRSC system of record. `us-east-1` and
`us-west-2` are active replicas; `us-east-2` is a witness and does not host
application compute. Sparse `gsi1` supports pending outbox queries. Sparse
`gsi2` supports dispatch-oriented access.

## Availability and recovery

Route 53 records can remove one site while retaining the other. Terraform
rejects disabling both sites. Routing isolation affects new globally routed
requests; it does not reassign existing work or drain queues across regions.
Regional worker interruption creates durable SQS backlog. Restoration resumes
normal processing.

## Deployment and rollback

Validate first, deploy and verify one regional application, deploy and verify
the peer, then update global routing. Roll back only the affected regional
application while preserving the healthy peer and application data.

## Security and privacy

Cognito JWT authorization protects product routes. Development-only synthetic
placement requires an explicit feature flag and authorized Cognito group.
Evidence and logs must exclude tokens, secrets, resume text, job descriptions,
prompts, provider bodies, queue URLs, and raw exception stacks.

## Explicit limitations

The current platform does not provide:

- automatic ownership reassignment based on health;
- automatic cross-Region queue draining;
- automatic replay of terminal failures;
- a public recovery API or operator console;
- zero-interruption guarantees for in-flight work;
- production activation of the publisher schedule without a separate decision.

## Evidence ledger

| Evidence | Report path | Result | Timestamp |
|---|---|---|---|
| Local-owner flow | `evidence/mr009d3b-*/` | Pending | Pending |
| Remote-owner flow | `evidence/mr009d3b-*/` | Pending | Pending |
| East isolation/restoration | `evidence/mr010-*/` | Pending | Pending |
| West isolation/restoration | `evidence/mr010-*/` | Pending | Pending |
| Backlog growth/drain | `evidence/mr010-*/` | Pending | Pending |
| MRSC visibility | `evidence/mr010-*/` | Pending | Pending |
| Regional rollback | `evidence/mr010-*/` | Pending | Pending |

Do not mark the program complete until every required row is successful or has
an explicitly accepted exception.
