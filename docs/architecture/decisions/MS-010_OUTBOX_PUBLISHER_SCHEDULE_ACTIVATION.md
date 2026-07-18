# MS-010: Controlled Outbox Publisher Schedule Activation

## Status

Accepted for development runtime validation.

## Context

MR-009D runtime validation must prove the normal asynchronous path:

```text
API
  -> durable outbox
  -> scheduled outbox publisher
  -> regional processing queue
  -> owner-region worker
```

The regional outbox-publisher Lambdas, EventBridge rules, targets, Lambda
permissions, DynamoDB access, and SQS send permissions exist. The schedules
were originally hard-coded `DISABLED` as an implementation gate while the
table, outbox publisher code, and data permissions were incomplete. That gate
became stale after MR-009A through MR-009D3A completed the publisher,
transport, route, and placement prerequisites.

Manual Lambda invocation, direct SQS sends, direct outbox mutation, replay,
retry, failover, traffic shifting, queue draining, and worker requeueing are
not valid substitutes for MR-009D runtime evidence.

## Decision

Make each regional outbox-publisher schedule explicitly configurable:

- root variable: `enable_outbox_publisher_schedule`;
- default: `false`;
- EventBridge rule state: `ENABLED` only when the variable is `true`;
- development runtime validation may set the variable to `true`;
- non-development environments cannot enable it until a later production
  activation decision changes policy.

The normal trigger is:

```text
EventBridge schedule
  -> same-region outbox-publisher Lambda
  -> bounded DynamoDB GSI query for dispatchable outbox records
  -> conditional claim to DISPATCHING
  -> local or owner-region SQS SendMessage
  -> conditional DELIVERED or failure state update
```

## Safety Properties

- Each active region has one local EventBridge rule, target, and Lambda invoke
  permission.
- The witness region has no publisher schedule, API, worker, queue, or DLQ.
- The publisher uses `Query` on the outbox status sparse GSI, not table scan.
- Duplicate dispatch is controlled by a conditional claim on outbox status,
  version, and dispatch lease state before any SQS send.
- Concurrent east and west publisher invocations may observe the same pending
  item, but only one can claim the item for a given dispatch attempt.
- Cross-region delivery remains a single SQS delivery attempt at the outbox
  boundary and does not introduce failover, replay, retry policy changes, owner
  reassignment, or health-based routing.
- Publisher IAM remains scoped to the Resume Analysis table and indexes plus
  active regional processing queues. It does not receive SQS receive/delete or
  DynamoDB scan permission.

## Consequences

MR-009D3B can be retried after development deployment verifies that both
regional schedules invoke the publisher normally against an empty outbox.

Production enablement remains disabled by default and requires a separate
explicit decision because scheduled dispatch changes operational behavior.

## MR-009D3C Observation

Deployment ID `3cdb262` proved that the configurable EventBridge schedules can
invoke the regional outbox-publisher Lambdas and that the deployed handler
entrypoint is `handler.handler`. The empty invocation proof did not pass:
publisher code attempted the accepted `gsi1` outbox status query, but the
deployed MRSC table does not define that index. The schedules were disabled
again through Terraform to stop recurring publisher errors. This decision
remains accepted as the scheduling model, but activation is blocked until the
DynamoDB table/index contract is aligned with repository code.

## MR-009D3D GSI Prerequisite

MR-009D3D aligns the deployed table with the repository query contract by adding
the sparse `gsi1` index in place: hash key `gsi1pk`, range key `gsi1sk`,
projection `ALL`. The index is required by outbox dispatch queries and by
entity fallback lookup paths in API and worker code.

Schedule enablement remains a separate phase. Development applies must first
add the index while `enable_outbox_publisher_schedule=false`, wait for the table
and `gsi1` to become `ACTIVE`, verify replica and witness health, and only then
apply `enable_outbox_publisher_schedule=true` to observe empty scheduled cycles.
If empty cycles fail, schedules must be disabled again through Terraform before
MR-009D3B is retried.
