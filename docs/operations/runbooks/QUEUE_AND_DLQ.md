# Queue, DLQ, and Outbox Operations

> **Status:** Canonical operator routing guide
> **Audience:** Operators and incident responders
> **Purpose:** Distinguish queue backlog, dead-letter, and publisher failures
> **Owner:** Operations
> **Related documents:** [Queue backlog and DLQ runbook](../platform-v2/QUEUE_BACKLOG_AND_DLQ_RUNBOOK.md), [outbox operations](../../runbooks/OUTBOX_OPERATIONS.md), [processing architecture](../../architecture/08_PROCESSING_ARCHITECTURE.md)

| Symptom | Procedure |
|---|---|
| Visible messages or oldest-message age increases | [Queue backlog and DLQ](../platform-v2/QUEUE_BACKLOG_AND_DLQ_RUNBOOK.md) |
| Messages appear in `processing_dlq` | [Queue backlog and DLQ](../platform-v2/QUEUE_BACKLOG_AND_DLQ_RUNBOOK.md) |
| Outbox event remains pending, claimed, or permanently failed | [Transactional outbox operations](../../runbooks/OUTBOX_OPERATIONS.md) |
| Worker event-source mapping is interrupted | [Multi-site operations](../platform-v2/MULTI_SITE_OPERATIONS_RUNBOOK.md) |
| Evidence is needed before mutation | [Incident evidence collection](../platform-v2/INCIDENT_EVIDENCE_COLLECTION_RUNBOOK.md) |

Preserve messages and evidence before replay. Diagnose ownership, workflow state, deployment identity, and the original failure before redrive. A queue retry, outbox replay, and owner transfer are different operations; none should be used as a substitute for another.
