# Processing Ownership

> **Status:** Canonical
> **Audience:** Architects, developers, operators
> **Purpose:** Explain why routing failover does not reassign existing work
> **Owner:** Application and Platform Engineering
> **Related documents:** [Processing architecture](../../architecture/08_PROCESSING_ARCHITECTURE.md), [MS-021](../../architecture/platform-resilience/MS-021_PROCESSING_OWNERSHIP.md)

Every newly created asynchronous work item has one durable `ownerRegion`. The persisted work record is authoritative. The queue message must agree with it, and only a worker executing in that region may claim the work.

Before processing, a worker strongly reads the record, validates message ownership, validates its current region, and performs a conditional claim that rechecks ownership and workflow state. A mismatch fails closed and remains visible through retry and DLQ behavior.

Global routing affects where new requests arrive. It does not update existing ownership. A controlled transfer would require isolation of the old consumer, a version-checked owner update, a new outbox event, redispatch, and unchanged idempotency/workflow guards. The repository does not automate that operation.

Traceability: [MS-005](../../architecture/decisions/MS-005_WORK_OWNERSHIP_AND_PLACEMENT.md), [MS-006](../../architecture/decisions/MS-006_CROSS_REGION_TRANSPORT_FOUNDATION.md), [MS-021](../../architecture/platform-resilience/MS-021_PROCESSING_OWNERSHIP.md), and [MR-014](../../certification/MR-014_MULTI_SITE_CERTIFICATION.md).
