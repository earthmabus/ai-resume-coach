# Multi-Site Completion Plan

## Goal

Finish the multi-site program before returning to product-feature development.

The foundation proves that the infrastructure composes correctly. The remaining work should prove that the application is diagnosable, traceable, deployable, and recoverable across both active sites.

## MR-009 — Multi-Site Application Integration

### MR-009A: Runtime Identity

Question answered:

> Which runtime handled this execution?

Potential diagnostic fields:

- AWS region
- logical site
- environment
- deployment ID
- application version
- Lambda function name

Requirements:

- one consistent contract for API and worker
- centralized configuration
- safe health metadata
- liveness remains dependency-free
- site-specific Terraform environment configuration
- focused Python and Terraform tests
- no routing, auth, message-contract, or topology changes

### MR-009A1: Regional Routing Foundation

Question answered:

> What configured regions can this runtime reason about?

Introduces centralized regional topology and pure routing decisions without
handler integration, forwarding, failover, or request rejection.

### MR-009A2: Work Ownership and Placement

Question answered:

> Which region owns this unit of work, and is this runtime in that region?

Introduces transport-neutral ownership resolution and placement evaluation.
New idempotency and outbox work records carry `ownerRegion`, and outbox-to-SQS
serialization preserves it. Transports still do not act on non-local placement.

### MR-009A3: Cross-Region Transport Foundation

Question answered:

> If this runtime is not the owner, how can asynchronous work be delivered to
> the owner region?

Introduces a domain-neutral regional delivery contract and SQS implementation
at the transactional outbox publisher boundary. Local placement still publishes
to the local `processing_queue`. Non-local placement makes one SQS delivery
attempt to the owning region's configured `processing_queue`.

No handler acts on placement, and this slice does not introduce failover,
transport retry, replay, queue draining, Route 53 changes, CloudFront changes,
or regional health policy.

### MR-009B: Correlation and Traceability

Question answered:

> How do we follow one unit of work end to end?

Desired flow:

```text
HTTP request
  -> API Lambda
  -> persisted request/outbox state
  -> SQS message
  -> worker Lambda
  -> completed or failed domain state
```

Potential identifiers:

- `requestId`: originating API command identifier
- `correlationId`: operational grouping identifier, validated from
  `X-Correlation-Id` or falling back to `requestId`
- durable work identifier
- `outboxEventId`
- SQS `transportMessageId`
- Lambda `runtimeInvocationId`
- owner and source region metadata

Constraints:

- preserve existing public and SQS contracts unless explicitly versioned
- do not expose user-sensitive values in logs
- reuse existing identifiers before inventing new ones
- avoid coupling tracing to one AWS region
- do not introduce distributed tracing, failover, or transport retry

### MR-009C: Operational Diagnostics

Question answered:

> What is deployed, where is it running, and is it alive?

Clarify and test:

- `/health`
- `/health/live`
- deployment/version/site diagnostics
- safe public metadata
- dependency-free liveness
- readiness semantics, if an existing route supports them
- passive regional-health classification:
  `HEALTHY`, `DEGRADED`, `UNAVAILABLE`, `UNKNOWN`
- explicit distinction between liveness, readiness, timestamped observations,
  and aggregate regional-health interpretation
- bounded health reason codes and freshness semantics
- symmetric, cost-gated application-region alarms for API, processing, outbox,
  transport, persistence, and configuration evidence
- witness-region health semantics limited to the accepted MRSC witness role

Do not create unrestricted diagnostic endpoints that expose configuration or infrastructure internals.
Do not use regional health for failover, routing, ownership reassignment,
transport retry, queue draining, or replay in this slice.

### MR-009D: Runtime Validation

Validate after deployment in a separately approved execution step:

- east and west identify themselves correctly
- traffic can be observed reaching both active sites
- deployment IDs are visible in safe diagnostics/logs
- queued work preserves correlation
- workers process in the expected region
- logs can reconstruct an end-to-end request

Do not deploy as part of implementation slices unless explicitly requested.

## MR-010 — Failover and Recovery Validation

Scenarios:

- isolate east; west remains active
- isolate west; east remains active
- reject disabling both sites
- worker unavailable; queue backlog grows
- worker recovery; backlog drains
- write/read behavior across MRSC active regions
- restored region rejoins safely
- rollback restores prior deployment

Each scenario needs:

- trigger
- expected behavior
- verification commands
- alarms/metrics/logs to inspect
- recovery steps
- evidence
- rollback or abort condition

## MR-011 — Operational Runbooks

Expected subjects:

- deployment
- rollback
- health verification
- regional isolation
- regional restoration
- queue backlog and DLQ response
- disaster recovery
- incident evidence collection

Runbooks must correspond to implemented and validated controls. Avoid generic copy that the platform cannot execute.

## MR-012 — Architecture Narrative

Complete the architecture book with current, evidence-based material covering:

- active-active topology
- request lifecycle
- data architecture
- shared processing capability
- security
- observability
- DR
- deployment
- decisions and tradeoffs
- future evolution

Clearly separate current capabilities from future options.

## Completion Criteria

Multi-site is complete when:

- infrastructure contracts remain green
- application runtime identity and traceability work in both sites
- operational diagnostics are safe and documented
- failover and recovery scenarios have validated procedures
- deployment and rollback are documented and exercised
- architecture documentation reflects actual behavior
- remaining risks and cost-gated controls are explicit
