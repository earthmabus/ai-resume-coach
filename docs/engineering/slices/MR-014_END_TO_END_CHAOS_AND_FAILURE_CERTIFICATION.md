# MR-014 — End-to-End Chaos and Failure Certification

## Purpose

Certify that the active-active platform continues to provide correct authenticated application behavior during bounded regional routing and worker-consumer failures, and that it returns to a healthy reconciled state afterward.

## Certification scenarios

1. **Safety invariant:** Terraform rejects disabling both application sites.
2. **Bidirectional routing isolation:** each Route 53 record is removed independently; the global endpoint converges to the survivor; an authenticated uploaded-resume workflow is accepted; owner-region semantics and cross-region reads are correct; routing is restored.
3. **Worker interruption:** one worker event-source mapping is disabled; a workflow is submitted twice with the same idempotency key; a durable queue backlog is observed; the worker is restored; the single workflow reaches `completed`; the queue drains.
4. **Post-recovery reconciliation:** both regional readiness endpoints, MRSC contract, and authenticated regional reads pass.

Every scenario must pass. Mutating scenarios must prove restoration. Partial execution is not certification.

## Safety

Mutations require `EXECUTE_CHAOS=YES` and `CONFIRM_MUTATION=YES`. Routing changes retain the MR-009D4 routing-only Terraform-plan check and EXIT-trap restoration. Worker interruption has an EXIT-trap that re-enables the event-source mapping.
