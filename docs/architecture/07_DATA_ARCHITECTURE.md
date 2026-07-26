# Data Architecture

> **Status:** Canonical
> **Audience:** Developers, data architects, operators
> **Purpose:** Define authoritative state, consistency, ownership, and document locality
> **Owner:** Platform Engineering
> **Related documents:** [Processing architecture](08_PROCESSING_ARCHITECTURE.md), [data consistency publication](../mvp2-disaster-recovery/architecture/DATA_CONSISTENCY.md), [single-table decision](decisions/MS-002_SINGLE_TABLE_FOR_NOW.md)

## Authoritative application state

The platform deliberately uses one DynamoDB table for resume-analysis and related workflow records. The table co-locates business state, idempotency records, work state, and transactional outbox records. Sparse secondary-index keys support outbox and entity access patterns without creating a table per entity.

The table uses DynamoDB multi-Region strong consistency with active replicas in `us-east-1` and `us-west-2` and witness responsibility in `us-east-2`. Strong replication does not eliminate application-level concurrency: conditional writes, version checks, idempotency keys, explicit workflow transitions, and deterministic ownership remain required.

## Ownership and placement

New asynchronous work records carry `ownerRegion`. The persisted owner is authoritative. Queue messages must agree with it, and only the worker in that region may claim the work. Routing changes do not mutate ownership. Legacy records without ownership metadata remain locally processable for compatibility.

## Idempotency and outbox state

API retries are scoped by user and operation and store a hashed idempotency key. Business records and the corresponding outbox event are created through the repository's transactional persistence protocols. Publishers conditionally claim pending events before delivery. Workers conditionally claim valid workflow states before provider execution.

## Documents

Documents are stored in regional, versioned S3 buckets associated with work ownership. Bidirectional replication, when enabled, copies new object versions and delete markers asynchronously to the peer region. It is best-effort, creates no replication loop, and does not backfill objects created before activation. Application code must not assume immediate peer availability.

This model preserves a clear distinction: DynamoDB is the strongly consistent system of record; S3 document continuity is asynchronous.
