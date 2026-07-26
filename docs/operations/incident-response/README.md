# Incident Response

> **Status:** Canonical operator index
> **Audience:** Incident responders and engineering leaders
> **Purpose:** Provide an incident entry point and route to failure-specific procedures
> **Owner:** Operations
> **Related documents:** [Incident response and review](../production/INCIDENT_RESPONSE_AND_REVIEW.md), [regional recovery](../../mvp2-disaster-recovery/operations/REGIONAL_RECOVERY.md)

1. Classify severity and establish incident ownership.
2. Preserve timestamps, deployment identity, health results, queue state, and relevant sanitized logs.
3. Identify the failure boundary before changing routing, workers, queues, identity, or documents.
4. Use the narrowest runbook and record every mutation.
5. Verify control-plane restoration, application outcomes, and durable state independently.
6. Complete a post-incident review with corrective actions.

Primary procedures:

- [Incident response and review](../production/INCIDENT_RESPONSE_AND_REVIEW.md)
- [Incident evidence collection](../platform-v2/INCIDENT_EVIDENCE_COLLECTION_RUNBOOK.md)
- [Regional isolation and recovery](../platform-v2/REGIONAL_ISOLATION_AND_RECOVERY_RUNBOOK.md)
- [Queue backlog and DLQ](../platform-v2/QUEUE_BACKLOG_AND_DLQ_RUNBOOK.md)
- [Outbox operations](../../runbooks/OUTBOX_OPERATIONS.md)

Never place tokens, secrets, raw resume content, prompts, provider payloads, physical resource identifiers, or unredacted exception bodies in durable incident evidence.
