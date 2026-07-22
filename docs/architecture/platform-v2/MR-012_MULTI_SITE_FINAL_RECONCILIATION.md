# MR-012 Multi-Site Final Reconciliation

## Status

**Reconciled and accepted.**

MR-012 introduced the non-mutating operational-readiness gate. MR-014 subsequently supplied the complete failure and recovery evidence. The final certification passed on July 22, 2026.

## Current topology

- Active application regions: `us-east-1`, `us-west-2`.
- DynamoDB MRSC witness region: `us-east-2`.
- Each active region contains an HTTP API, API Lambda, outbox publisher, SQS processing queue, DLQs, worker Lambda, document bucket, and regional logs.
- Cognito identity and the DynamoDB system of record are shared capabilities.
- Route 53 latency routing publishes the sites enabled by `site_routing_enabled` and uses regional readiness health checks.

## Request and processing lifecycle

A protected request enters one regional HTTP API. The API derives runtime identity, request ID, correlation ID, and an idempotency fingerprint. Asynchronous work and its outbox record are persisted atomically. The work record carries deterministic `ownerRegion`. A scheduled publisher dispatches the event to the owner-region SQS queue. The regional worker validates ownership and workflow state before processing.

Duplicate API, publisher, queue, and worker deliveries are controlled through idempotency, conditional writes, and explicit workflow transitions.

## Data architecture

The ResumeAnalysis table is the MRSC system of record. `us-east-1` and `us-west-2` are active replicas. `us-east-2` supplies the witness responsibility and hosts no application API, worker, queue, or document bucket. Sparse indexes support pending outbox and dispatch access patterns.

Document storage remains regional. Work ownership identifies the site responsible for document access and processing.

## Availability and recovery

Routing isolation removes one Route 53 latency record while leaving that regional stack directly reachable for diagnosis. New globally routed requests converge to the surviving site. Existing work is not reassigned.

Worker interruption leaves work durably queued. Restoring the event-source mapping resumes processing. The certification harness verifies restoration rather than assuming the enabling request has completed.

## Deployment and rollback

Deploy and validate one regional application, deploy and validate its peer, then change global routing separately. Roll back only the affected regional application package or configuration. Infrastructure rollback must not attempt to reverse durable application data.

## Security and privacy

Cognito JWT authorization protects product routes. Synthetic placement is development-only, feature-gated, and restricted to an authorized Cognito group. Evidence and logs must exclude tokens, secrets, resume text, job descriptions, prompts, provider payloads, and raw exception bodies.

## Certification ledger

| Evidence | Result | Authoritative record |
|---|---|---|
| Both-sites-disabled guard | PASS | MR-014 certification record |
| East isolation/restoration | PASS | MR-014 certification record |
| West isolation/restoration | PASS | MR-014 certification record |
| Authenticated survivor work | PASS | MR-014 certification record |
| Cross-region reads and owner-region correctness | PASS | MR-014 certification record |
| Worker backlog growth/restoration/drain | PASS | MR-014 certification record |
| Duplicate idempotency | PASS | MR-014 certification record |
| Post-recovery readiness and MRSC health | PASS | MR-014 certification record |

See `docs/certification/MR-014_MULTI_SITE_CERTIFICATION.md`.

## Accepted limitations

The platform does not provide automatic ownership reassignment, automatic cross-Region queue draining, automatic terminal-failure replay, a public recovery console, or a zero-interruption guarantee for in-flight work. Full WAF, alarm, dashboard, and synthetic-monitoring activation is a separate production-hardening decision.

## Final conclusion

The architecture documented in Platform V2 matches the deployed implementation and its observed behavior. Multi-site active-active is implemented, operable, and runtime-certified.
