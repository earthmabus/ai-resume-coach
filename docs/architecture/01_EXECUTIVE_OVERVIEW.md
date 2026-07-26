# Executive Overview

> **Status:** Canonical
> **Audience:** Engineering leaders, hiring managers, architects
> **Purpose:** Provide the shortest accurate architecture orientation
> **Owner:** Platform Engineering
> **Related documents:** [Platform overview](02_PLATFORM_OVERVIEW.md), [executive summary](../executive/EXECUTIVE_SUMMARY.md), [architecture publications](README.md)

AI Resume Coach is an AI-assisted career-development product backed by a secure, observable, serverless AWS platform. It supports target-career management, resume analysis, resume tailoring, and job matching while serving as an evidence-backed example of multi-site engineering.

The implemented system runs peer application sites in `us-east-1` and `us-west-2`. Route 53 latency routing selects healthy enabled APIs. Both sites read and write a single DynamoDB multi-Region strongly consistent system of record; `us-east-2` provides the witness responsibility. Each active site owns regional compute, queues, DLQs, logs, and document storage.

Correctness is explicit. API workflows use idempotency and a transactional outbox. Durable `ownerRegion` state governs asynchronous work independently of the runtime receiving a request. The owner-region worker validates persisted ownership and workflow state before processing. Regional health is diagnostic and does not silently reassign work.

The architecture has completed controlled multi-site failure certification. The certified envelope includes isolation of either global route, survivor-region work, cross-region reads, worker interruption, durable backlog, duplicate submission, restoration, queue drain, and reconciliation. Production certification is a separate, stricter profile and must not be inferred from architectural completion.

Continue with the [platform overview](02_PLATFORM_OVERVIEW.md), then use the [architecture index](DOCUMENT_INDEX.md) to follow the concern relevant to your role.
