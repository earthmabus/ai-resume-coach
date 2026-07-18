# Operational Runbook

Operational procedures, validation, incidents, and recovery.

## Regional Health Checks

Use `/health/live` to verify that a regional Lambda process can execute. This
endpoint is dependency-free and should not be treated as proof that the region
can process application work.

Use `/health/ready` to inspect the local region's readiness checks and passive
readiness-scoped `regionalHealth` classification:

- `HEALTHY`: all required fresh observations for the classified scope pass.
- `DEGRADED`: one or more meaningful capabilities are impaired while useful
  service remains.
- `UNAVAILABLE`: the classified capability cannot perform its required role.
- `UNKNOWN`: evidence is missing, stale, contradictory, or insufficient.

Readiness observations include UTC `observedAt`, `freshnessSeconds`, `fresh`,
and bounded `reasonCode` fields. Treat stale observations as unknown evidence,
not as current health.

The classification is diagnostic only. It does not reassign work ownership,
change placement, alter routing, retry delivery, drain queues, replay work, or
trigger failover.

## Regional Health Investigation

Start with the narrowest known signal:

- API degradation: check `/health/live`, `/health/ready`, API Gateway 5xx and
  latency alarms, API Lambda errors and throttles, and API structured logs with
  `requestId`, `correlationId`, `currentRegion`, and `deploymentId`.
- Worker degradation: check worker Lambda errors and throttles, the
  `WorkerRecordFailures` alarm, processing queue age and depth, DLQ depth, and
  worker logs with `workId`, `outboxEventId`, `transportMessageId`, and
  `runtimeInvocationId`.
- Queue backlog: check `ApproximateNumberOfMessagesVisible`,
  `ApproximateAgeOfOldestMessage`, worker concurrency, worker throttles, and
  DLQ depth. A backlog can mean `DEGRADED` processing while API readiness still
  succeeds.
- Outbox or transport failure: check the outbox publisher Lambda error alarm,
  `OutboxPublishFailures`, outbox records in retryable state, and publisher or
  regional-transport logs with `outboxEventId`, `ownerRegion`, `sourceRegion`,
  `currentRegion`, and `transportMessageId` when SQS accepted a message.
- DynamoDB impairment: check `/health/ready`, DynamoDB throttling or service
  alarms, API and worker errors, and whether work remains durably recoverable
  in idempotency and outbox records.
- Missing monitoring data: verify traffic expectations, deployment state,
  CloudWatch metric availability, alarm missing-data treatment, and whether
  the absence of data is normal for the signal.
- Secondary-region impairment: compare the same endpoint, alarm, queue,
  worker, outbox, and DynamoDB signals in east and west. Do not infer that the
  primary region has richer or more authoritative health semantics.
- Witness impairment: inspect the MRSC data contract and DynamoDB global-table
  status for the witness responsibility. The witness is not an application
  site and has no application health endpoint, worker, queue, or regional
  transport path.

Current recovery boundaries are the existing durable records, SQS queues, DLQ,
and outbox retry process. The platform does not automatically reroute traffic,
reassign owners, retry cross-region transport inside the transport layer, drain
queues, replay work, or fail over based on health classification.

## Readiness Latency

`/health/ready` performs two sequential AWS dependency checks after
configuration loads:

- DynamoDB `DescribeTable`
- SQS `GetQueueAttributes`

Each SDK client uses a one-second connection timeout, a one-second read
timeout, and one SDK attempt. Normal responses should be much faster than that.
During dependency impairment, expect the endpoint to fail within a small,
bounded window rather than waiting on default SDK retry behavior. Cold starts
and API Gateway overhead still apply.

## Alarm Guide

Use alarms as capability signals, not as proof of whole-region availability:

- API 5xx: request path degradation. Inspect API Gateway metrics, API Lambda
  errors, and API logs.
- API latency: request path slowness. Compare east and west latency before
  assuming a regional incident.
- Lambda errors: execution failures in API, worker, or outbox publisher.
- Lambda throttles: capacity or concurrency pressure. Check reserved/account
  concurrency and recent deployments.
- Queue depth: processing backlog exists. Existing queued work is still
  durable.
- Oldest-message age: processing is falling behind. Check worker errors,
  throttles, and DLQ.
- DLQ messages: failed messages require manual investigation. Alarm recovery
  does not mean DLQ contents were processed.
- DynamoDB throttles: persistence pressure. Readiness may still pass during
  intermittent throttling.
- Worker record failures: per-record worker failures were emitted in sustained
  periods. Use worker logs and correlation fields.
- Outbox publish failures: the publisher failed to dispatch local or regional
  SQS work in sustained periods. Use outbox records and publisher logs.

All current error, backlog, and custom-failure alarms treat missing data as
not breaching. That is intentional because these are not heartbeat metrics.
Use deployment validation, synthetic health checks, resource inspection, and
dashboard review to detect missing resources or disabled monitoring.

## Alarm-to-Log Queries

For worker-record failures, start with the worker log group and query:

```sql
fields @timestamp, component, operation, result, JobType, RecordId,
  RequestId, CorrelationId, OutboxEventId, OwnerRegion, SourceRegion,
  MessageId, @message
| filter WorkerRecordFailures > 0 or result = "FAILURE"
| sort @timestamp desc
| limit 50
```

For outbox-publish failures, start with the outbox publisher log group and
query:

```sql
fields @timestamp, component, operation, result, requestId, correlationId,
  workId, outboxEventId, ownerRegion, sourceRegion, currentRegion,
  transportMessageId, deliveryStatus, failureCategory, @message
| filter OutboxPublishFailures > 0 or result = "FAILURE"
| sort @timestamp desc
| limit 50
```

Keep identifiers in logs. Do not add request IDs, correlation IDs, work IDs,
outbox event IDs, SQS message IDs, runtime invocation IDs, or user IDs as
metric dimensions.

## Readiness and Alarm Disagreement

Treat disagreement as useful evidence:

- Ready is healthy, queue age is alarming: API dependencies are reachable, but
  asynchronous processing is degraded.
- Ready fails, workers still process: API readiness is impaired while queued
  work may continue. Ownership has not changed.
- API error alarm fires, ready returns 200: the shallow readiness probe passed,
  but real request traffic is failing. Inspect API logs and metrics.
- Outbox failures alarm, queue and workers look healthy: existing queued work
  may process, but newly created work may not reach SQS.

Do not collapse these into one aggregate regional status.

## Monitoring Disabled

When operational alarms or dashboards are disabled, outputs should show disabled
or empty monitoring resources. Metrics may still be emitted through AWS-native
service metrics and EMF logs, but alarms will not notify or change state.

Production readiness validation requires the approved controls when production
readiness enforcement is enabled. Do not interpret missing alarms as healthy.

## Safe Manual Actions

Operators may:

- call regional `/health/live` and `/health/ready`;
- inspect dashboards, alarms, metrics, queue depth, queue age, DLQ depth,
  Lambda errors, throttles, and DynamoDB throttles;
- query structured logs using request, correlation, work, outbox, transport,
  and runtime identifiers;
- inspect outbox state through supported repository tooling or operational
  procedures;
- validate regional Terraform outputs and deployment configuration;
- roll back an application or infrastructure release through accepted
  deployment procedures.

Operators must not assume support for automatic failover, traffic shifting,
owner reassignment, replay, queue draining, transport retry, health-state
override, regional fencing, or manual data mutation unless a later approved
runbook introduces it.

## Rollout and Verification

Recommended rollout:

1. Run local validation and Terraform tests.
2. Review the Terraform plan for alarm, dashboard, output, and IAM changes.
3. Deploy to a non-production or accepted lower environment first.
4. Verify `/health/live` and `/health/ready` in east and west.
5. Confirm `regionalHealth.scope` is `readiness` and observation timestamps are
   current.
6. Confirm bounded reason codes and sanitized dependency failures.
7. Confirm alarms are created only when monitoring is enabled.
8. Confirm dashboard widgets show API, Lambda, queue, custom worker/outbox, and
   DynamoDB signals for both active regions.
9. Confirm metric dimensions remain bounded.
10. Confirm the witness remains limited to the MRSC data role.
11. Roll out production through the accepted regional deployment order.
12. Observe alarms, dashboard widgets, logs, and health endpoints after
    deployment.

Rollback triggers include unexpected health schema incompatibility, readiness
latency outside the expected bounded window, missing regional symmetry,
incorrect alarm dimensions, or unsafe public health output.

Rollback must not alter ownership, routing, queue contents, outbox records, or
durable business data. Removing alarms can remove future signal but does not
recover failed work.

## Recovery Verification

Use capability-specific recovery checks:

- readiness: `/health/ready` returns 200 with fresh observations;
- API degradation: API 5xx or latency alarm returns to OK and request logs stop
  showing failures;
- worker degradation: worker-record failure alarm returns to OK, queue age and
  depth fall, and worker logs show successful processing;
- outbox degradation: outbox-publish failure alarm returns to OK and pending or
  retryable outbox records are investigated;
- DLQ: DLQ depth must be inspected and handled manually; an alarm clearing does
  not prove replay;
- DynamoDB throttling: throttling metrics return to normal and affected
  request/worker logs stop showing persistence failures;
- witness: MRSC validation and DynamoDB global-table status return to the
  expected state.

Recovery never implies ownership transfer, failover, queue draining, replay,
or lost-work recovery unless a later approved mechanism performs and verifies
that action.
