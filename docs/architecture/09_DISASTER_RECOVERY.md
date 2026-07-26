# Disaster Recovery

> **Status:** Canonical
> **Audience:** Architects, operators, incident responders
> **Purpose:** Summarize the implemented recovery model and certified boundaries
> **Owner:** Platform Engineering and Operations
> **Related documents:** [MVP2 disaster recovery](../mvp2-disaster-recovery/README.md), [operations portal](../operations/README.md), [MR-014 certification](../certification/MR-014_MULTI_SITE_CERTIFICATION.md)

The platform uses two active application sites, a shared MRSC system of record, global latency routing, regional queues and documents, and explicit processing ownership. Recovery is designed as bounded, observable operator action rather than hidden ownership reassignment.

## Failure behavior

- **API site isolation:** remove one Route 53 latency record while keeping the regional stack directly reachable. New global requests converge on the surviving site.
- **Worker interruption:** disable the affected event-source mapping and allow its regional SQS backlog to remain durable. Restore the mapping, verify it reaches `Enabled`, then verify workflow completion and queue drain.
- **Document continuity:** use asynchronously replicated peer copies for new objects covered by the replication configuration; do not assume zero lag or historical backfill.
- **Identity outage:** use the warm-standby Cognito recovery foundation through a controlled migration and password-reset process. This is not seamless failover.
- **Existing owned work:** do not automatically reassign it. Any owner transfer requires isolation of the original consumer, version-checked persistence, a new outbox event, and redispatch.

## Certified boundary

MR-014 certified isolation of either routing record, authenticated survivor-region work, deterministic ownership, cross-region reads, worker interruption, durable backlog, idempotent duplicate submission, restoration, workflow completion, queue drain, and final reconciliation.

The certification does not establish automatic ownership reassignment, automatic cross-region queue draining, terminal-failure replay, zero interruption, a public recovery console, measured contractual RTO/RPO, whole-account recovery, or production-profile readiness.

Concept publications, validation methods, certification evidence, and editable diagrams live under [docs/mvp2-disaster-recovery](../mvp2-disaster-recovery/README.md).
