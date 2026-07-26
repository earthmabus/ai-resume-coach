# Regional Isolation and Recovery

> **Status:** Canonical operator routing guide
> **Audience:** Operators and incident responders
> **Purpose:** Select the correct procedure while preserving safety invariants
> **Owner:** Operations
> **Related documents:** [Regional isolation runbook](../../operations/platform-v2/REGIONAL_ISOLATION_AND_RECOVERY_RUNBOOK.md), [multi-site operations](../../operations/platform-v2/MULTI_SITE_OPERATIONS_RUNBOOK.md)

## Choose the failure boundary

| Observation | Primary procedure |
|---|---|
| One global route is unhealthy or must be isolated | [Regional isolation and recovery](../../operations/platform-v2/REGIONAL_ISOLATION_AND_RECOVERY_RUNBOOK.md) |
| A regional worker is unavailable or backlog grows | [Queue backlog and DLQ](../../operations/platform-v2/QUEUE_BACKLOG_AND_DLQ_RUNBOOK.md) |
| An outbox event is stuck or permanently failed | [Outbox operations](../../runbooks/OUTBOX_OPERATIONS.md) |
| Evidence must be preserved | [Incident evidence collection](../../operations/platform-v2/INCIDENT_EVIDENCE_COLLECTION_RUNBOOK.md) |
| A controlled exercise is authorized | [Controlled chaos runbook](../../operations/platform-v2/MR-014/CONTROLLED_CHAOS_RUNBOOK.md) |

## Invariants

- Never disable both global site records.
- Do not destroy a regional stack to isolate routing.
- Do not treat DNS convergence as work-ownership transfer.
- Preserve queues and evidence before replay or cleanup.
- Verify control-plane restoration reaches its terminal state.
- Verify application outcome, workflow state, and queue drain independently.
- Do not expose sensitive payloads in incident artifacts.
