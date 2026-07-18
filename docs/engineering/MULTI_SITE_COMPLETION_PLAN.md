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

- request ID
- correlation ID
- idempotency key where safe
- work identifier
- work type

Constraints:

- preserve existing public and SQS contracts unless explicitly versioned
- do not expose user-sensitive values in logs
- reuse existing identifiers before inventing new ones
- avoid coupling tracing to one AWS region

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

Do not create unrestricted diagnostic endpoints that expose configuration or infrastructure internals.

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
