# Data Consistency and Document Continuity

> **Status:** Canonical
> **Audience:** Architects, developers, operators
> **Purpose:** Separate strongly consistent state from asynchronous document replication
> **Owner:** Platform Engineering
> **Related documents:** [Data architecture](../../architecture/07_DATA_ARCHITECTURE.md), [MS-020](../../architecture/platform-resilience/MS-020_DOCUMENT_REPLICATION.md)

DynamoDB is the authoritative system of record. The single table has MRSC replicas in both active application regions and a witness in `us-east-2`. Application correctness still depends on conditional writes, idempotency, explicit workflow state, and durable ownership.

Documents use regional S3 buckets. When bidirectional Cross-Region Replication is enabled, original writes in either active region produce a peer copy. Replication is asynchronous and best-effort. It covers new object versions, tags, and delete markers; it does not backfill older objects or create recursive replication loops.

The two consistency models serve different needs:

| Data | Authority | Cross-region behavior |
|---|---|---|
| Business, idempotency, work, outbox state | DynamoDB MRSC table | Strongly consistent replicas |
| Resume and related documents | Owner-region S3 bucket | Asynchronous replicated copy |

No documentation or application flow should imply that a just-uploaded document is immediately present in the peer region.
