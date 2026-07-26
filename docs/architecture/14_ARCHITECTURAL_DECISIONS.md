# Architectural Decisions

> **Status:** Canonical
> **Audience:** Architects, developers, engineering leaders
> **Purpose:** Index accepted decisions and their consequences
> **Owner:** Architecture
> **Related documents:** [Decision records](decisions/), [Platform V2 decisions](platform-v2/ARCHITECTURE_DECISIONS.md), [architecture publications](README.md)

The decision records preserve why the implemented platform has its current boundaries. They remain authoritative until a later accepted decision explicitly supersedes them.

## Core decisions

- [ADR-001](decisions/ADR-001_SERVERLESS_ARCHITECTURE.md): adopt managed serverless architecture.
- [MS-001](decisions/MS-001_MULTI_SITE_TOPOLOGY.md): operate peer application sites in `us-east-1` and `us-west-2` with an MRSC witness in `us-east-2`.
- [MS-002](decisions/MS-002_SINGLE_TABLE_FOR_NOW.md): retain one DynamoDB table until materially different domain needs justify decomposition.
- [MS-003](decisions/MS-003_SHARED_PROCESSING_CAPABILITY.md): retain shared `processing_queue` and `processing_dlq` capabilities.
- [MS-004](decisions/MS-004_RUNTIME_IDENTITY.md): treat runtime identity as diagnostic metadata.
- [MS-005](decisions/MS-005_WORK_OWNERSHIP_AND_PLACEMENT.md): keep durable ownership separate from runtime placement and health.
- [MS-006](decisions/MS-006_CROSS_REGION_TRANSPORT_FOUNDATION.md): begin cross-region delivery at the transactional-outbox boundary.
- [MS-007](decisions/MS-007_CORRELATION_AND_TRACEABILITY.md): preserve explicit logical and operational correlation identifiers.
- [MS-008](decisions/MS-008_REGIONAL_HEALTH_CLASSIFICATION.md): keep health passive and diagnostic.
- [MS-009](decisions/MS-009_DEVELOPMENT_SYNTHETIC_PLACEMENT_OVERRIDE.md): restrict deterministic placement override to authorized development validation.
- [MS-010](decisions/MS-010_OUTBOX_PUBLISHER_SCHEDULE_ACTIVATION.md): activate publisher schedules through an explicit, bounded contract.
- [MR-013](decisions/MR-013_EXPLICIT_WORKFLOW_STATE_MACHINE.md): make workflow transitions explicit and compatibility-aware.

## Platform boundaries

The [platform-layer ADR package](decisions/platform-layers/README.md) separates shared foundation, global ingress, regional application, and production-operations overlays. [Platform V2 decisions](platform-v2/ARCHITECTURE_DECISIONS.md) summarize implementation-specific decisions and accepted non-goals.

Decision status is not inferred from file age. Revisit a decision only through a new record that names the prior decision, the changed evidence, migration consequences, and validation.
