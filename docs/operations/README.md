# Operations Portal

> **Status:** Canonical
> **Audience:** Operators, release engineers, incident responders
> **Purpose:** Route operational tasks to concise, executable procedures
> **Owner:** Operations
> **Related documents:** [Architecture operational guide](../architecture/13_OPERATIONAL_RUNBOOK.md), [disaster recovery](../mvp2-disaster-recovery/operations/README.md), [certification](../certification/README.md)

## Select a task

| Task | Start here |
|---|---|
| Deploy or rebuild safely | [Deployment](deployment/README.md) |
| Review health, dashboards, alarms, or synthetics | [Monitoring](monitoring/README.md) |
| Triage and manage an incident | [Incident response](incident-response/README.md) |
| Handle queue backlog, DLQ, or outbox failures | [Queue and DLQ](runbooks/QUEUE_AND_DLQ.md) |
| Isolate or restore one application site | [Regional recovery](../mvp2-disaster-recovery/operations/REGIONAL_RECOVERY.md) |
| Capture sanitized incident evidence | [Evidence collection](platform-v2/INCIDENT_EVIDENCE_COLLECTION_RUNBOOK.md) |
| Run non-destructive validation | [Validation](validation/README.md) |
| Conduct an authorized failure exercise | [Controlled chaos](platform-v2/MR-014/CONTROLLED_CHAOS_RUNBOOK.md) |
| Review operating roles, objectives, and reviews | [Production operations](production/README.md) |

Procedural runbooks remain separate so operators can execute them under pressure. Architecture publications explain why; runbooks specify prerequisites, commands, abort conditions, restoration, and evidence.

Mutating commands require explicit authorization. Do not run deployment, routing isolation, worker interruption, replay, or certification exercises merely to inspect documentation.
