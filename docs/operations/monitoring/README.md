# Monitoring

> **Status:** Canonical operator index
> **Audience:** Operators and incident responders
> **Purpose:** Route health, logs, metrics, alarms, dashboards, and synthetic checks
> **Owner:** Operations
> **Related documents:** [Observability architecture](../../architecture/10_OBSERVABILITY.md), [production observability](../../architecture/platform-resilience/MS-023_PRODUCTION_OBSERVABILITY.md)

Use `/health/live` for process liveness and `/health/ready` for bounded dependency readiness. Neither endpoint is proof of end-to-end workflow success, and readiness never mutates routing or ownership.

The current monitoring contract includes structured correlation fields, native AWS metrics, a shared operations dashboard, curated regional alarms, recent error-log views, and global/east/west synthetic checks when their feature flags are enabled.

Operator references:

- [Architecture operational guide](../../architecture/13_OPERATIONAL_RUNBOOK.md)
- [Service objectives and KPI catalog](../production/SERVICE_OBJECTIVES_AND_KPIS.md)
- [Incident evidence collection](../platform-v2/INCIDENT_EVIDENCE_COLLECTION_RUNBOOK.md)
- [Queue backlog and DLQ](../platform-v2/QUEUE_BACKLOG_AND_DLQ_RUNBOOK.md)

Alarm state and notification delivery are separate. An alarm with no action can still detect a condition, but it does not notify an operator.
