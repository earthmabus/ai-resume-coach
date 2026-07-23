# MR-013 — Explicit Workflow State Machine

## Decision

Workflow lifecycle transitions are governed by one application-level policy in
`src/core/workflow_state.py`. Dispatch and worker persistence boundaries must
validate the current and target workflow status before issuing a DynamoDB
mutation.

## Scope

This decision governs business-workflow records such as resume analysis, job
matching, resume tailoring, and interview preparation. It does not merge the
independent state machines for idempotency records, transactional outbox
records, SQS transport delivery, or dispatch leases.

## Compatibility

MR-013 intentionally preserves the status values already stored and returned by
the application. The slice adds authoritative transition rules without a data
migration or an API compatibility break.

## Correctness properties

- Terminal workflow states cannot be reclaimed or overwritten.
- Retryable failures may return only to worker processing.
- Dispatch may advance a workflow only from `QUEUED_PENDING_DISPATCH` to
  `QUEUED`, and the DynamoDB condition must verify that source state still
  exists at write time.
- Worker claims and outcomes are validated before conditional writes.
- Unknown or invalid transitions fail closed with a clear exception.
- DynamoDB conditional expressions remain the final concurrency control at the
  persistence boundary.

## Terraform compatibility

MR-013 does not change the DynamoDB key model. The current AWS provider schema
continues to use table-level `hash_key` and `range_key` arguments while the GSI
contract remains unchanged. Terraform schema modernization is not required to
complete the workflow-state decision and must not be represented as part of
this slice unless provider support is verified in the deployed toolchain.

## Evidence

Run `./tools/validate/workflow_state.sh` to export the
complete status vocabulary, legal transition graph, terminal-state set, and
contract-validation result under `evidence/mr013-<timestamp>/`.
