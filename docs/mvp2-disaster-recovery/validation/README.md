# Disaster-Recovery Validation

> **Status:** Canonical index
> **Audience:** Developers, operators, auditors
> **Purpose:** Separate assessment, bounded exercise, chaos certification, and readiness policy
> **Owner:** Platform Engineering and Operations
> **Related documents:** [MS-022](../../architecture/platform-resilience/MS-022_DISASTER_RECOVERY_VALIDATION.md), [validation contract](../../engineering/VALIDATION_CONTRACT.md)

| Validation level | Mutation | Proves |
|---|---|---|
| Repository validation | None beyond local build artifacts | Code, Terraform, tests, and architecture contracts agree |
| DR assessment | Read-only cloud inspection | Routing, health, workers, queues, identity recovery, replication configuration, and ownership controls are present |
| Bounded replication exercise | Two sentinel objects with cleanup | New east-to-west and west-to-east object replication within the polling window |
| Controlled chaos | Approval-gated service mutation | Bounded routing and worker failure behavior plus recovery |
| Readiness assessment | Read-only policy evaluation | A named environment profile passes its required controls |

The [MR-014 certification runbook](../../operations/platform-v2/MR-014/END_TO_END_CHAOS_CERTIFICATION_RUNBOOK.md) is the executable controlled-failure procedure. The [MR-014 certification record](../../certification/MR-014_MULTI_SITE_CERTIFICATION.md) is the durable result.
