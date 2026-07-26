# Executive Summary

> **Status:** Canonical
> **Audience:** Engineering leaders, hiring managers, product leaders, architects
> **Purpose:** Explain the product value, engineering strategy, and verified readiness posture
> **Owner:** Engineering Leadership
> **Related documents:** [Platform overview](PLATFORM_OVERVIEW.md), [operational readiness](OPERATIONAL_READINESS.md), [architecture overview](../architecture/01_EXECUTIVE_OVERVIEW.md)

AI Resume Coach helps users establish a target career, analyze resume evidence, tailor resumes, and compare resumes with job opportunities. The repository pairs that product journey with a mature engineering reference implementation: secure identity, regional serverless APIs and workers, durable asynchronous workflows, Infrastructure as Code, observability, disaster recovery, and evidence-based certification.

The platform is intentionally disciplined rather than infrastructure-heavy. Two peer AWS application sites serve traffic in `us-east-1` and `us-west-2`. A DynamoDB multi-Region strongly consistent table is the system of record, with `us-east-2` serving only as its witness. Regional queues and documents preserve failure isolation, while explicit work ownership prevents traffic routing from silently changing business semantics.

Business value comes from more than availability. Idempotency, a transactional outbox, explicit workflow states, correlation identifiers, bounded health responses, and approval-gated recovery tools make failures diagnosable and retries safe. The design demonstrates how AI-enabled product work can coexist with security, operational transparency, cost controls, and reviewable architecture decisions.

The active-active architecture has completed final acceptance and controlled failure certification. That evidence covers either-site routing isolation, authenticated survivor-region work, cross-region reads, worker interruption, durable backlog, duplicate submission, recovery, queue drain, and reconciliation. The durable readiness record passes the pre-production profile.

Production certification remains deliberately separate. The production profile requires environment controls—including protective and notification configuration—that are not implied by architectural completion or a pre-production pass. The repository therefore demonstrates both delivery confidence and honest status language.

For technical detail, use the [architecture publication set](../architecture/README.md). For the evidence and operational boundary, see [operational readiness](OPERATIONAL_READINESS.md).
