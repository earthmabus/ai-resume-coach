# Multi-Site Architecture Diagram Portfolio

> **Status:** Canonical publication home
> **Audience:** Engineering leaders, architects, operators, incident responders
> **Purpose:** Organize the active-active and disaster-recovery body of work by enduring concept
> **Owner:** Platform Engineering and Operations
> **Related documents:** [Canonical disaster recovery](../architecture/09_DISASTER_RECOVERY.md), [operations portal](../operations/README.md), [certification](../certification/README.md)

This directory is the primary publication home for the multi-site active-active and disaster-recovery program. Concept pages explain the current design; milestone records remain at their established paths for traceability; formal certification remains under `docs/certification/`.

## Read by concept

- [Topology and global routing](architecture/TOPOLOGY_AND_ROUTING.md)
- [Identity recovery](architecture/IDENTITY_RECOVERY.md)
- [Data consistency and document continuity](architecture/DATA_CONSISTENCY.md)
- [Processing ownership](architecture/PROCESSING_OWNERSHIP.md)
- [Regional isolation and recovery](operations/REGIONAL_RECOVERY.md)
- [Validation and controlled exercises](validation/README.md)
- [Readiness and certification](certification/README.md)
- [Diagram catalog](diagrams/README.md)

This directory contains the final Director-level diagram set for the implemented and runtime-certified AI Resume Coach multi-site active-active architecture.

Each diagram is available as:

- `.svg` for scalable repository and browser rendering;
- `.png` for presentations, profiles, and documents;
- `.dot` as the editable Graphviz source of truth.

## Diagram set

1. **Executive multi-site architecture** — the full global, shared, regional, data, and witness topology.
2. **C4 context** — people, the AI Resume Coach, external providers, AWS, email, and CI/CD.
3. **C4 container** — browser, edge, identity, regional application, shared data, provider, and operations boundaries.
4. **Runtime request and workflow** — authenticated request through transactional persistence, outbox dispatch, queue delivery, worker claim, and result visibility.
5. **Failure recovery and certification** — the routing-isolation and worker-interruption scenarios proven during MR-014.
6. **Data ownership and consistency** — the distinction between shared MRSC state and region-bound queues and document storage.
7. **Architecture evolution timeline** — the progression from the original single-region MVP to MR-016 final acceptance.

## Authoritative architecture basis

The posters are explanatory assets, not executable contracts. Architecture claims are governed by the numbered architecture publications, Terraform contracts, application tests, supported operational tooling, and formal certification records.

The diagrams reflect:

- `docs/architecture/platform-v2/PLATFORM_V2_ARCHITECTURE.md`
- `docs/architecture/platform-v2/MR-016_FINAL_ACCEPTANCE.md`
- `docs/certification/MR-014_MULTI_SITE_CERTIFICATION.md`
- `docs/operations/platform-v2/MULTI_SITE_OPERATIONS_RUNBOOK.md`

They intentionally preserve the accepted boundaries and non-goals: deterministic owner-region placement, regional S3 document ownership, no automatic ownership reassignment, no automatic cross-region queue draining, and no contractual RTO/RPO claim.
