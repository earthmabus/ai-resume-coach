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

## Next Multi-Site Objective

Before returning to product engineering, finish multi-site operational readiness.

The first likely implementation slice is runtime identity:

- region
- logical site
- environment
- deployment ID
- application version
- Lambda function name where available

Runtime identity should be:

- derived from centralized configuration
- available consistently to API and worker code
- included in safe operational diagnostics and structured log context
- dependency-free
- deterministic in unit tests
- diagnostic only

It must not:

- make authorization decisions
- determine tenancy
- drive routing
- expose sensitive infrastructure values

The exact implementation has not yet been chosen. Inspect existing health, API handler, worker handler, configuration, tests, and Terraform environment blocks before proposing changes.
