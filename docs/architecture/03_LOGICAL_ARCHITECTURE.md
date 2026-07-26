# Logical Architecture

> **Status:** Canonical
> **Audience:** Developers and architects
> **Purpose:** Explain responsibilities and dependency boundaries independent of AWS placement
> **Owner:** Platform Engineering
> **Related documents:** [Physical architecture](04_PHYSICAL_ARCHITECTURE.md), [request lifecycle](06_REQUEST_LIFECYCLE.md), [processing architecture](08_PROCESSING_ARCHITECTURE.md)

## Product domains

The product layer owns target-career management, resume analysis, resume tailoring, job matching, and related user-facing workflows. Product records use domain language such as `resume_analysis`; infrastructure capability names do not redefine product requirements.

## Reusable platform capabilities

- **Identity:** authenticates users and supplies claims to protected API routes.
- **Request context:** carries request, correlation, deployment, site, and runtime identifiers without turning diagnostics into authorization state.
- **Persistence:** stores authoritative business, idempotency, workflow, and outbox records.
- **Processing:** accepts typed work through the shared `processing_queue` and isolates exhausted deliveries in `processing_dlq`.
- **Document storage:** retains regional source documents and supports asynchronous peer replication when enabled.
- **Observability:** emits structured logs, bounded health responses, metrics, alarms, dashboards, and synthetic checks.
- **Recovery and validation:** provides read-only assessments, approval-gated exercises, runbooks, and durable certification records.

## Dependency direction

Regional API handlers call domain and core abstractions. They do not use runtime identity as a tenancy or routing decision. Asynchronous requests persist business state and an outbox event before transport occurs. Publishers deliver to the queue named by durable placement; workers validate persisted ownership and workflow state before invoking providers or mutating the workflow.

External AI providers sit behind application abstractions. Provider failure must remain observable and retry-compatible; it does not alter the ownership, idempotency, or persistence contracts.

## Boundary principles

- One DynamoDB table remains the accepted system-of-record design.
- The shared processing queue and DLQ remain capability-oriented resources.
- Public health responses expose bounded diagnostics, never secrets or physical resource identifiers.
- Global traffic routing, identity recovery, document replication, and work ownership are related resilience concerns but are not one automatic failover mechanism.
