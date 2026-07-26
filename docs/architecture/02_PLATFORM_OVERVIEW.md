# Platform Overview

> **Status:** Canonical
> **Audience:** Engineering leaders, developers, architects
> **Purpose:** Describe the implemented platform and its boundaries
> **Owner:** Platform Engineering
> **Related documents:** [Logical architecture](03_LOGICAL_ARCHITECTURE.md), [physical architecture](04_PHYSICAL_ARCHITECTURE.md), [system capabilities](../executive/SYSTEM_CAPABILITIES.md)

AI Resume Coach combines career-development workflows with a serverless AWS platform. Users authenticate, manage a target career, submit resume evidence, request analysis, tailor resumes, and compare them with opportunities. The application separates those product concerns from reusable identity, persistence, asynchronous processing, observability, and recovery capabilities.

The implemented platform has two peer application sites in `us-east-1` and `us-west-2`. Route 53 latency routing can direct new API requests to either healthy enabled site. A single DynamoDB multi-Region strongly consistent table is the authoritative state store, with replicas in both active sites and a witness in `us-east-2`. Each active site owns its API, compute, processing queue, DLQs, logs, and document bucket.

The architecture favors explicit correctness over invisible failover. Durable `ownerRegion` state governs work placement; runtime region is diagnostic metadata. Routing isolation changes where new requests arrive but does not silently transfer existing asynchronous work. Conditional writes, idempotency, the transactional outbox, and explicit workflow transitions make retries observable and safe.

The multi-site design is architecturally accepted and was certified through controlled routing isolation, survivor-region work, cross-region reads, worker interruption, backlog recovery, duplicate submission, and final reconciliation. That certification does not claim automatic ownership transfer, whole-account recovery, zero interruption, or production-profile certification.

The platform includes cost-gated dashboards, alarms, synthetics, WAF controls, and recovery features. Whether a control is present in Terraform, enabled in an environment, or required by a readiness profile are separate facts. See [validation and certification](12_VALIDATION_AND_CERTIFICATION.md).
