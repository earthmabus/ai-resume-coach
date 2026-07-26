# Glossary

> **Status:** Canonical
> **Audience:** All readers
> **Purpose:** Define platform terms used across executive and technical publications
> **Owner:** Architecture
> **Related documents:** [Reference glossary](../reference/GLOSSARY.md), [architecture decisions](../architecture/14_ARCHITECTURAL_DECISIONS.md)

| Term | Definition |
|------|------------|
| AI Resume Coach | The platform described by this repository. |
| Active-active application sites | The `us-east-1` and `us-west-2` peer sites that can accept API traffic and own work. This does not imply every dependency is active-active. |
| Agentic usage | A shared usage allowance for supported agent-style product features; unrelated to platform runtime architecture. |
| Disaster recovery | Controlled practices used to isolate failures, preserve state, restore service, and prove recovery. |
| Infrastructure as Code | Infrastructure managed through declarative configuration. |
| Observability | Logs, metrics, dashboards, alarms, and health signals used to understand system behavior. |
| MRSC | DynamoDB multi-Region strong consistency. The platform uses active replicas in east and west plus a witness in `us-east-2`. |
| `ownerRegion` | Durable authority for processing and document locality; separate from the region currently executing code. |
| `processing_queue` | Shared asynchronous processing capability provisioned regionally. |
| Readiness profile | Environment-specific policy applied by the common readiness engine. |
| Runtime identity | Diagnostic deployment, site, and region metadata; never authorization or tenancy state. |
