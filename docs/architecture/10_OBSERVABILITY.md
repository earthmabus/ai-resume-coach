# Observability

Metrics, logs, tracing, dashboards, alarms, and health checks.

## Correlation Fields

Structured logs use consistent, payload-safe correlation fields where they are
available:

- `requestId`
- `correlationId`
- `workId`
- `outboxEventId`
- `transportMessageId`
- `runtimeInvocationId`
- `sourceRegion`
- `currentRegion`
- `ownerRegion`
- `eventType`
- `deploymentId`

These identifiers allow an operator to move between API logs, idempotency
records, work records, outbox records, SQS delivery evidence, worker logs, and
final work state. They must not include resume content, job descriptions,
tokens, raw message bodies, or other sensitive payload data.

High-cardinality identifiers such as request IDs, correlation IDs, work IDs,
outbox event IDs, and SQS message IDs belong in structured log fields, not
CloudWatch metric dimensions.

The platform does not currently run a distributed tracing service such as AWS
X-Ray or OpenTelemetry. Correlation is a logging and durable-contract model,
not a tracing backend.

Canonical runtime and transport fields are `runtimeInvocationId` and
`transportMessageId`. Existing diagnostics may also emit `awsRequestId` or
`deliveryMessageId` as compatibility aliases.

## Regional Health

Regional health is passive diagnostic evidence for an application region. It
does not drive routing, placement, ownership, retries, replay, queue draining,
or failover.

The vocabulary is:

- liveness: a process or endpoint can execute and return a response;
- readiness: the local runtime has the required configuration and dependencies
  to accept or process its intended work;
- observation: a bounded, timestamped operational fact with a freshness window;
- regional health status: a summarized classification for an explicit scope.

The current statuses are:

- `HEALTHY`
- `DEGRADED`
- `UNAVAILABLE`
- `UNKNOWN`

`/health/live` remains dependency-free and reports only that the Lambda process
can execute. `/health/ready` observes configuration, DynamoDB, and SQS
readiness and includes safe observations plus a readiness-scoped
`regionalHealth` object for the local runtime. That object carries
`scope: readiness`; it is not an aggregate claim that every regional capability
is healthy. Readiness SDK calls use bounded one-second connection and read
timeouts with one SDK attempt per dependency check.

Observation payloads use bounded reason codes and UTC timestamps. Stale,
missing, contradictory, or unrecognized evidence produces `UNKNOWN` rather
than silently becoming healthy.

The regional health dimensions are:

- API: liveness, readiness, API Gateway 5xx, API Lambda errors, throttles, and
  latency.
- Processing: processing queue depth, oldest-message age, worker Lambda errors,
  worker throttles, and bounded worker record failures.
- Outbox and transport: outbox publisher Lambda errors and bounded
  `OutboxPublishFailures`, including local and regional SQS delivery failures.
- Persistence: DynamoDB throttles and service errors, plus request-time
  readiness dependency results.
- Configuration: required runtime configuration, regional identity, topology,
  and queue mapping validity.

Operational alarms remain cost-gated. The curated regional set covers API
availability and latency, Lambda role errors, queue age and depth, DLQ depth,
DynamoDB throttling, sustained worker record failures, and sustained outbox
publish failures. Missing data treatment is explicit and signal-specific; the
current error/backlog/custom-failure alarms treat missing data as not breaching
because absence of those datapoints is normal when no traffic or failures are
present.

Metric dimensions must remain bounded: `region`, `environment`, `component`,
`operation`, `result`, `FunctionName`, `QueueName`, `TableName`, `ApiId`, and
`Stage` are acceptable when applicable. High-cardinality identifiers such as
`requestId`, `correlationId`, `workId`, `outboxEventId`,
`transportMessageId`, and `runtimeInvocationId` must remain log fields, not
metric dimensions.

The DynamoDB witness region is not an application-serving site. Witness health
is interpreted through the MRSC data contract, Terraform validation, DynamoDB
service metrics, and runbook checks; no witness application endpoint or full
regional monitoring stack is created by this architecture.

The operations dashboard compares both active regions and includes API errors
and latency, Lambda errors and throttles, queue health, custom worker/outbox
failure metrics, DynamoDB throttles, synthetic health success when enabled,
and a regional error-log query.

Regional health does not change ownership, routing, placement, transport,
retry, replay, queue draining, or failover behavior.
