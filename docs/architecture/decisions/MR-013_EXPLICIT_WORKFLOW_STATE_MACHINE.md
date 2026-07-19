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
  `QUEUED`.
- Worker claims and outcomes are validated before conditional writes.
- Unknown or invalid transitions fail closed with a clear exception.
- DynamoDB conditional expressions remain the final concurrency control at the
  persistence boundary.

## Terraform maintenance

The DynamoDB table and both GSIs use `key_schema` blocks. Deprecated
`hash_key` and `range_key` arguments are removed without changing the logical
partition or sort keys.
