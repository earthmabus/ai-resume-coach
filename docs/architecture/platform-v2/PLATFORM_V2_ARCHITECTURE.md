# Platform V2 Multi-Site Architecture

## Executive summary

Platform V2 is a symmetric, two-site serverless application deployed in `us-east-1` and `us-west-2`. Both sites accept authenticated API traffic and can own asynchronous work. A DynamoDB multi-Region strongly consistent table provides the shared system of record, with the configured witness responsibility in `us-east-2`.

The design was runtime-certified on July 22, 2026 through bounded routing isolation, survivor-region application work, cross-region reads, worker interruption, durable backlog, idempotent replay, restoration, and post-recovery reconciliation.

## Topology

### Global and shared capabilities

- Route 53 latency records and health checks for the global API hostname
- shared Cognito user pool and web client
- shared registration notification path
- frontend S3 and CloudFront distribution
- DynamoDB MRSC system of record
- package construction and Terraform orchestration

### Per-active-site capabilities

Each active site contains:

- API Gateway HTTP API
- API Lambda
- outbox publisher Lambda and one-minute schedule
- processing queue, processing DLQ, and terminal-failure DLQ
- worker Lambda and event-source mapping
- regional S3 document bucket
- regional application and access logs

## Request flow

1. Route 53 selects a healthy active API site.
2. API Gateway validates the Cognito JWT.
3. The API derives request, correlation, runtime, and idempotency context.
4. A transaction persists the workflow and outbox record.
5. Deterministic placement records `ownerRegion`.
6. The scheduled publisher dispatches to the owner-region queue.
7. The owner-region worker validates ownership and state, processes the document, and persists a terminal or retryable workflow state.
8. The result is readable through either active API replica.

## Consistency and ownership

DynamoDB MRSC supplies strongly consistent multi-region application state. Strong consistency does not remove the need for idempotency, conditional writes, explicit workflow transitions, or deterministic ownership.

`ownerRegion` identifies the processing and document-storage boundary. Regional health does not automatically mutate ownership. Existing work remains associated with its owner region during routing isolation.

## Routing and failure behavior

Route 53 latency routing distributes new requests across healthy enabled sites. Disabling one site's routing record removes it from the global API without destroying the regional stack. The direct regional endpoint remains available for diagnosis and recovery.

Terraform rejects a configuration in which both site routing records are disabled.

A disabled worker event-source mapping causes SQS backlog to accumulate durably. Re-enabling and confirming the mapping reaches `Enabled` resumes processing. Queue drain and workflow completion are verified independently.

## Deployment and rollback

Application deployment is regional and sequential:

```text
validate → deploy one site → verify direct site → deploy peer → verify direct peer → change global routing separately
```

Rollback is scoped to the affected regional package or configuration. Durable business data is not reversed by infrastructure rollback.

## Security boundaries

Cognito JWT authorization protects application routes. The synthetic placement override exists only to create deterministic validation scenarios. It is feature-gated, restricted to an authorized Cognito group, and not a production ownership mechanism.

Tokens, secrets, resume text, job descriptions, prompts, provider payloads, and sensitive presigned material are excluded from durable certification documentation.

## Observability

Regional health endpoints expose runtime identity and bounded dependency readiness. Structured logs propagate request, correlation, work, outbox, transport, deployment, region, and site identifiers. Native AWS metrics and optional dashboards, alarms, and synthetics provide additional signals when enabled.

Readiness is diagnostic. It does not perform failover, ownership reassignment, queue replay, or traffic mutation.

## Certified failure envelope

The architecture is certified for:

- isolation of either global routing record;
- continued authenticated work through the surviving site;
- deterministic survivor ownership for new work;
- cross-region reads from the MRSC system of record;
- regional worker-consumer interruption;
- durable queue backlog;
- idempotent duplicate submission;
- restoration and workflow completion;
- final queue drain and multi-site reconciliation.

## Accepted non-goals

- automatic ownership reassignment;
- automatic cross-region queue consumption or draining;
- automatic terminal-failure replay;
- zero-interruption processing guarantees;
- public operator recovery APIs;
- whole-account disaster recovery;
- full production-hardening control activation;
- contractual RTO/RPO commitments.

## Authoritative references

- `docs/certification/MR-014_MULTI_SITE_CERTIFICATION.md`
- `docs/operations/platform-v2/MULTI_SITE_OPERATIONS_RUNBOOK.md`
- `docs/architecture/platform-v2/MR-016_FINAL_ACCEPTANCE.md`
