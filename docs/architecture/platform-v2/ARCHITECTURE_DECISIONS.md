# Platform V2 Architecture Decisions

## Final decisions

### P2-001 — Clean rebuild

Destroy and rebuild rather than preserve legacy Terraform addresses because the environment was low-risk and long-term architecture quality was more valuable than address continuity.

### P2-002 — Symmetric regional module

Both active sites use one regional Terraform module. Region-specific behavior is configuration, not duplicated implementation.

### P2-003 — Shared identity

One Cognito user pool and client serve both regional APIs.

### P2-004 — Shared edge and global API hostname

The frontend remains globally served through CloudFront. The API hostname uses Route 53 latency routing across regional API Gateway custom domains.

### P2-005 — DynamoDB MRSC system of record

The final data topology uses active replicas in `us-east-1` and `us-west-2` with witness responsibility in `us-east-2`. The witness is not an application site.

### P2-006 — Regional document and messaging boundaries

Each active site owns its document bucket, queue, DLQs, publisher, worker, and execution path. Work is delivered to the deterministic owner-region queue.

### P2-007 — Transactional outbox to SQS

The durable outbox remains the dispatch boundary. EventBridge is used only as the publisher schedule, not as the work transport. SQS is the regional work transport.

### P2-008 — Deterministic ownership, not health-driven reassignment

`ownerRegion` is assigned deterministically and persisted. Health classification and routing isolation do not rewrite ownership or move existing queue contents.

### P2-009 — Idempotency and explicit workflow state

API retries, publisher retries, SQS redelivery, and worker retries are expected. Conditional writes, idempotency fingerprints, and explicit workflow states make duplicate delivery safe.

### P2-010 — Latency routing with a both-disabled guard

Both active sites may serve traffic. Terraform prevents disabling both routing records. Isolation removes only the selected Route 53 record and preserves the direct regional stack.

### P2-011 — Validation-only synthetic placement

Synthetic placement is allowed only in an explicitly enabled development validation configuration and for an authorized Cognito group. It is not a general user feature or production routing policy.

### P2-012 — Explicitly authorized chaos

Mutating certification requires `EXECUTE_CHAOS=YES` and `CONFIRM_MUTATION=YES`. Every mutation includes restoration logic and evidence.

## Implementation pivots

- The secondary active site changed from `us-west-1` to `us-west-2` to support the selected MRSC design.
- The transport design converged on SQS-only work delivery; EventBridge remains only as the periodic publisher trigger.
- Regional routing decisions remained transport-agnostic rather than embedding forwarding behavior in the API handler.
- Runtime certification introduced deterministic child evidence directories so orchestration consumes the exact scenario output it created.
- Terraform validation now aligns plan inputs with deployed Lambda runtime identity to avoid unrelated package or configuration drift during routing-only exercises.
- Worker backlog certification replaced a fixed delay with bounded polling because the publisher runs on a one-minute schedule.
- Worker restoration is not considered complete until the event-source mapping reports `Enabled`.

## Consequences

The platform continues through bounded loss of a routing site and tolerates worker interruption without losing queued work. The design deliberately accepts that existing work is not automatically reassigned and that production-hardening controls are a separate operational maturity decision.
