# MS-021 — Regional Processing Ownership

## Status

Implemented as a deterministic worker-enforcement and operational-contract slice.

## Decision

Every newly created asynchronous work item has one authoritative `ownerRegion`.
The persisted work record is authoritative when it contains that field. The SQS
message must agree with the persisted owner, and only a worker running in that
region may claim the work.

Route 53 failover does not change `ownerRegion`. HTTP traffic failover and
asynchronous work ownership are separate concerns. This slice therefore does
not infer ownership from health, DNS, runtime identity, or the region that
happens to receive a retry.

## Worker authorization sequence

Before a worker changes workflow state or invokes an AI provider, it performs:

1. A strongly consistent read of the work record.
2. Validation that message `ownerRegion` agrees with persisted `ownerRegion`.
3. Validation that the current worker region equals the authoritative owner.
4. A conditional DynamoDB claim that also checks `ownerRegion` has not changed.

The fourth condition closes the race where an operator transfers ownership
after the read but before the claim. A failed condition causes the record to be
retried rather than processed by two regions.

Legacy records and messages that predate ownership metadata remain locally
processable for backward compatibility. New work continues to carry explicit
ownership through idempotency records, outbox records, and queue messages.

## Failover boundary

The platform already routes new requests to a surviving healthy API site and
routes newly published work to its owner-region queue. MS-021 does not add:

- automatic ownership reassignment;
- automatic cross-region SQS queue draining;
- health-based owner mutation;
- worker requeueing to a peer region;
- an operator-facing recovery API.

These exclusions preserve the certified multi-site boundary and avoid a hidden
split-brain control plane.

## Controlled owner transfer

A future or manually approved recovery procedure may perform a controlled owner
transfer only when all of the following are true:

1. The original owner is isolated or its consumer is stopped.
2. The durable work record is updated with a version-checked conditional write.
3. A new outbox event is created for the replacement owner.
4. The replacement message is delivered to the replacement regional queue.
5. Existing idempotency and workflow-state conditions remain authoritative.

This repository does not automate that mutation in MS-021. The Terraform output
names the model `CONTROLLED_PERSISTED_OWNER_UPDATE_AND_REDISPATCH` so operators
do not confuse routing failover with ownership transfer.

## Split-brain protections

- persisted owner validation;
- message owner validation;
- current-region authorization;
- conditional owner check during claim;
- versioned workflow-state transition;
- idempotent terminal and completion behavior.

## Deployment workflow

```bash
./tools/resilience/activate_processing_ownership.sh plan

CONFIRM_MUTATION=YES \
  ./tools/resilience/activate_processing_ownership.sh apply

./tools/resilience/activate_processing_ownership.sh validate
```

The plan preserves the enabled MS-018 global-routing, MS-019 identity-recovery,
and MS-020 document-replication settings.

## Operational interpretation

A non-owner worker fails closed and returns the SQS record as a partial-batch
failure. It does not invoke a provider or mutate workflow state. Persistent
misrouting will eventually follow the queue's existing retry and DLQ policy,
which keeps the failure visible rather than silently acknowledging lost work.
