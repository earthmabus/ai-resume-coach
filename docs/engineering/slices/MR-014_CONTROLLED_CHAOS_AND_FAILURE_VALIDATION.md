# MR-014 — Controlled Chaos and Failure Validation

## Objective

Turn the existing MR-010 recovery exercises into a bounded chaos-validation program with explicit authorization, restoration requirements, and consolidated evidence.

## Scenarios

1. Terraform rejects disabling both sites.
2. East isolation, west survivor validation, east restoration.
3. West isolation, east survivor validation, west restoration.
4. Regional worker interruption, backlog retention, worker restoration, queue drain.

MR-014 does not add automatic failure injection. Every mutating scenario requires `EXECUTE_CHAOS=YES` and `CONFIRM_MUTATION=YES` and delegates to the already reviewed MR-010 harness.

## Acceptance

- MR-012 readiness passes before mutation.
- No scenario can disable both sites.
- Every mutating scenario has a named restoration action.
- A PASS cannot be recorded without restoration evidence.
- Reports are written below `evidence/mr014-*`.
