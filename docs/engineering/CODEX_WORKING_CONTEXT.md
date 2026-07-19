# Codex Working Context

## Purpose

This document captures decisions that were previously discussed outside the repository so a coding agent can work from durable, reviewable context.

It is not a substitute for inspecting the source. The repository remains the implementation source of truth.

## Current Checkpoint

The Platform V2 infrastructure foundation was completed and validated at commit:

```text
7dd518e — dr - completed infra upgrade
```

A local milestone tag was created:

```text
infra-foundation-v2
```

At that checkpoint, the user reported:

- 203 Python tests passing
- 28 Terraform tests passing
- `terraform validate` successful
- `./tools/validate_platform_v2_foundation.sh` successful
- Platform V2 multi-site production-readiness validation successful

Re-run validation before relying on these counts because the repository may have changed.

## Completed Infrastructure Direction

Platform V2 composes two active regional application sites:

- East: `us-east-1`
- West: `us-west-2`

DynamoDB uses multi-region strong consistency with:

- active data regions: `us-east-1`, `us-west-2`
- witness region: `us-east-2`

The regional modules are intended to remain symmetric peers.

Enterprise-style controls such as enhanced observability, WAF, health checks, and similar cost-bearing features should remain explicitly cost-gated where the repository already follows that pattern.

## Domain Vocabulary Refactor

Generic data terminology was replaced with Resume Analysis terminology across active Terraform contracts.

Examples:

```text
application_table      -> resume_analysis_table
APPLICATION_TABLE      -> RESUME_ANALYSIS_TABLE
application_data       -> resume_analysis_data
data_contract          -> resume_analysis_contract / resume_analysis
```

The intent is one ubiquitous language across application configuration, infrastructure resources, IAM, outputs, observability, and executable Terraform specifications.

Do not reintroduce generic `application_*` naming for authoritative Resume Analysis data.

## Data Decision

The application currently stores multiple item types in one DynamoDB table.

This was reviewed deliberately. The decision is to keep the table intact for now because it preserves:

- straightforward transactional writes
- co-location of domain state, idempotency, and outbox items
- simpler MRSC topology
- simpler monitoring, IAM, Terraform, and operational management
- existing access patterns and compatibility

This is not a permanent prohibition on decomposition. Revisit table boundaries only when bounded domains show materially different ownership, scaling, retention, security, resilience, or lifecycle needs.

Do not create one table per entity.

## Messaging Decision

The SQS resources represent a reusable platform processing capability, not a Resume Analysis-owned transport.

Retain:

```text
processing_queue
processing_dlq
```

Do not rename those Terraform resources or outputs to `resume_analysis_queue` or similar names.

Messages may contain typed work such as:

```text
RESUME_ANALYSIS
JOB_MATCHING
RESUME_TAILORING
```

Queue separation should occur only when workloads need materially different:

- scaling
- latency
- retry or DLQ behavior
- security boundaries
- failure isolation
- operational ownership

A feature-facing environment variable may remain domain-oriented when it accurately describes that feature's dependency on the shared queue. Inspect current code and Terraform before changing any variable contract.

## Existing Runtime Patterns

Current code includes:

- immutable `AppConfig` in `src/core/config.py`
- cached `get_config()`
- centralized required environment-variable handling
- immutable `RequestContext` in `src/core/request_context.py`
- thin compatibility entrypoints in root `handler.py` and `worker.py`

There is no dedicated `logging.py` or `telemetry.py` module at the current checkpoint.

Do not introduce a logging framework simply to satisfy a task. First inspect current logging behavior in the real API and worker implementations.

Configuration describes deployment/runtime facts. Request context describes facts that vary per request. Preserve this distinction.

## Current Multi-Site Application Direction

MR-009A, MR-009A1, MR-009A2, ARR-001, MR-009A3, ORR-001, ENG-001,
MR-009B, ARR-002, and MR-009C have established the application-side
active-active foundation:

- runtime identity remains diagnostic metadata
- regional topology and routing configuration are centralized
- work ownership is separate from runtime identity
- placement evaluation is transport-neutral
- newly created idempotency and outbox work records carry `ownerRegion`
- outbox-to-SQS serialization preserves `ownerRegion`
- the transactional outbox publisher is the first cross-region transport
  boundary for asynchronous work
- end-to-end correlation uses explicit `requestId`, `correlationId`,
  `workId`, `outboxEventId`, `transportMessageId`, and
  `runtimeInvocationId` meanings
- regional health classification is passive diagnostic state with
  `HEALTHY`, `DEGRADED`, `UNAVAILABLE`, and `UNKNOWN` statuses
- regional health separates liveness, readiness, timestamped observations,
  freshness, bounded reason codes, and aggregate operator interpretation
- active application regions use symmetric health semantics; the `us-east-2`
  witness remains limited to its DynamoDB MRSC witness responsibility

MR-009A3 introduces one SQS delivery attempt from the outbox publisher to the
owning region's configured `processing_queue` when placement is non-local.
Local placement continues to publish to the local regional queue.

MR-009B standardizes traceability without distributed tracing infrastructure.
Request context validates `X-Correlation-Id` and falls back to the API Gateway
request ID. Idempotency, work, outbox, queue messages, publisher diagnostics,
and worker diagnostics preserve that correlation where available. Legacy
compatible records and messages without `correlationId` remain usable.

Handlers must not act on non-local placement. The current foundation does not
implement HTTP forwarding, worker requeueing, failover, health-based routing,
traffic shifting, queue draining, replay, or transport retry.

Regional health must not be used to reassign ownership, change placement,
route traffic, retry transport, drain queues, replay work, or trigger failover
until a later accepted decision explicitly introduces that behavior.

MR-009C does not persist aggregate health state. Request-time readiness exposes
safe local observations, while sustained regional degradation is evaluated
through cost-gated CloudWatch alarms, structured logs, metrics, and runbooks.

## MR-009D Runtime Validation Status

MR-009D is still open. MR-009D3A deployed route-contract alignment and the
development-only synthetic placement override at deployment ID `ef79140`.
MR-009D3B then verified the pre-write runtime gates but did not create
synthetic business work because the normal outbox publisher trigger is not
operational: both regional EventBridge publisher schedules are deployed but
disabled, and Terraform tests require them to remain disabled.

Before attempting the end-to-end synthetic workflow again, repository
authority must be updated through an accepted remediation that lets the outbox
publisher run through a normal trigger or another explicitly approved
validation dispatch mechanism. Do not use manual SQS sends, direct outbox
mutation, replay, retry, failover, traffic shifting, or worker requeueing as
substitute MR-009D evidence.

MR-009D3C selects the normal EventBridge schedule as that trigger and controls
it with `enable_outbox_publisher_schedule`. The flag defaults to `false`; the
development runtime validation deployment sets it to `true`; non-development
enablement is rejected until a later production activation decision. The
publisher safety model is a bounded GSI query plus conditional claim before
delivery, so concurrent regional schedules do not rely on timing jitter for
duplicate-dispatch protection.

MR-009D3C deployed the explicit schedule control and corrected the publisher
Lambda handler wiring at deployment ID `3cdb262`. EventBridge then reached the
publisher application code in both active regions, but empty scheduled cycles
failed because the deployed DynamoDB MRSC table does not define the `gsi1`
index used by `core.outbox_publisher`, `core.storage`, and worker entity
lookups. The schedules were disabled again through Terraform to stop recurring
publisher errors. MR-009D remains open until repository authority adds and
validates the sparse `gsi1` table/index contract or otherwise changes the
accepted query model. Do not retry MR-009D3B synthetic work while this blocker
is present.

MR-009D3D completed the prerequisite remediation at deployment ID `2b87e4d`.
The deployed table now has sparse `gsi1` with string keys `gsi1pk`/`gsi1sk`
and `ALL` projection. The index was added with schedules disabled, reached
`ACTIVE`, and the development schedules were then enabled. East and west
publishers completed empty EventBridge-triggered cycles with zero counts and no
errors. MR-009D remains open; the next slice is MR-009D3B synthetic
end-to-end validation. Do not start MR-010.
