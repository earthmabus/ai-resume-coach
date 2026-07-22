# MR-013 — Explicit Workflow State Machine

## Intent

Make the workflow lifecycle an explicit, executable application contract rather than a collection of status strings distributed across API, publisher, and worker code.

## Implemented capability

The authoritative vocabulary and legal transitions live in:

```text
src/core/workflow_state.py
```

Publisher and worker persistence boundaries call `assert_transition(...)` before mutation. DynamoDB conditional expressions remain the final concurrency guard.

Run the contract validator with:

```bash
./tools/multi_site/mr013_workflow_state_validation.sh
```

It writes:

```text
evidence/mr013-<timestamp>/workflow-state-contract.json
```

## Correctness guarantees

- Unknown statuses and unknown transitions fail closed.
- Terminal states have no outbound transitions.
- Retryable failures can only be reclaimed into worker processing.
- Publisher dispatch advances only `QUEUED_PENDING_DISPATCH` to `QUEUED`.
- Publisher completion requires DynamoDB to still contain `QUEUED_PENDING_DISPATCH`; a stale in-memory item cannot overwrite a concurrent state change.
- Worker claim and outcome writes require the expected status and processing ownership.
- Existing API status values remain compatible; no data migration is introduced.

## Validation

The slice includes:

- complete transition-matrix tests;
- worker claim-state and race tests;
- a publisher stale-write regression test;
- a machine-readable state-contract validator;
- evidence generation suitable for later DR certification.

## Explicit exclusions

MR-013 does not merge idempotency, outbox, SQS delivery, dispatch-lease, or terminal-failure publication states into the business workflow state machine. Those remain separate bounded state models.

MR-013 also does not perform chaos injection or DR certification. Those remain later milestones.
