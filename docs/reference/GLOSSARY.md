# Technical Glossary

> **Status:** Canonical
> **Audience:** Developers, architects, operators
> **Purpose:** Define implementation and operating terminology
> **Owner:** Architecture
> **Related documents:** [Executive glossary](../executive/GLOSSARY.md), [architectural decisions](../architecture/14_ARCHITECTURAL_DECISIONS.md)

| Term | Meaning |
|---|---|
| Correlation ID | Validated diagnostic grouping identifier propagated across request and asynchronous boundaries. |
| Deployment ID | Diagnostic identifier for the deployed package/configuration; not authorization state. |
| Idempotency | Contract that repeated equivalent commands do not create duplicate authoritative work. |
| MRSC | DynamoDB multi-Region strong consistency. |
| Outbox | Durable event stored with business state and later conditionally claimed for transport. |
| Owner region | Persisted authority for processing and document locality. |
| Processing queue | Shared asynchronous capability provisioned once per active application site. |
| Readiness | Bounded dependency state used for diagnostics and health checks; never an ownership mutation. |
| Runtime identity | Site, region, deployment, and invocation diagnostics. |
| Witness region | `us-east-2` DynamoDB MRSC witness responsibility, not an application site. |
