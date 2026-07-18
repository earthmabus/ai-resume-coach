# MS-008: Regional Health Classification Is Passive Diagnostic State

## Status

Accepted

## Decision

Expose a small regional-health vocabulary and passive classification model for
the local application-region runtime:

- `HEALTHY`: all required, sufficiently fresh observations for the classified
  capability pass.
- `DEGRADED`: one or more meaningful capabilities are impaired while useful
  service capability remains.
- `UNAVAILABLE`: the classified capability cannot perform its required
  application-region role.
- `UNKNOWN`: evidence is missing, stale, contradictory, unavailable, or
  insufficient.

Regional health is diagnostic state. It is not ownership state, routing state,
placement state, failover state, or authorization state.

The existing `/health/live` endpoint remains dependency-free. The existing
`/health/ready` endpoint remains the readiness boundary and includes safe
request-time observations plus a readiness-scoped `regionalHealth` object. That
object includes `scope: readiness` and must not be treated as proof of
aggregate application-region health.

Observations and classifications are separate concepts. An observation is a
bounded, timestamped operational fact with a dimension, check name, status,
freshness window, safe reason code, region, and deployment identifier.
Application-created observations are limited to the checks the runtime
actually performs. Classification interprets a set of fresh observations for
an explicit scope.

Health responses and diagnostics use bounded reason codes instead of raw
exception text. The current reason-code set is intentionally small:

- `ALL_REQUIRED_CHECKS_PASS`
- `CONFIGURATION_INVALID`
- `DEPENDENCY_UNAVAILABLE`
- `PARTIAL_DEPENDENCY_FAILURE`
- `OBSERVATION_STALE`
- `OBSERVATION_MISSING`
- `OBSERVATION_UNRECOGNIZED`

Application-region monitoring is evaluated through a combination of:

- synchronous liveness and readiness checks;
- AWS-native API Gateway, Lambda, SQS, and DynamoDB metrics;
- bounded application metrics for worker record failures and outbox publishing
  failures;
- cost-gated CloudWatch alarms;
- operator runbooks.

The DynamoDB witness region remains limited to its MRSC witness role. It is
not an application-serving region and does not receive application health
endpoints, workers, queues, regional transport, or application alarm symmetry.

## Rationale

MR-009A through MR-009B established runtime identity, ownership, placement,
transport, and correlation without regional health policy. Later multi-site
slices need a consistent way to describe whether a regional runtime appears
healthy, degraded, unavailable, or unknown before any failover or recovery
behavior is considered.

Keeping classification passive preserves the current layering:

```text
Runtime Identity
  -> Health Observation
  -> Health Classification
  -> Future Policy
```

## Consequences

- Health classification can be logged, returned from readiness, represented by
  alarms, and used by operators for diagnosis.
- Request-time readiness classification answers the current local readiness
  question; sustained regional degradation is represented by CloudWatch alarms
  and operator interpretation, not by a single synchronous endpoint.
- Stale observations classify as `UNKNOWN`; historical success must not be
  reported as current health.
- There is no application health table or persisted aggregate health record.
  CloudWatch alarm state and logs are the operational record for aggregate
  health evidence in this slice.
- Health classification must not reassign `ownerRegion`.
- Health classification must not change routing, placement, transport, retry,
  replay, queue draining, or failover behavior.
- Liveness remains process-only and does not call DynamoDB, SQS, or
  configuration-dependent readiness checks.
- Public health responses must remain free of secrets, ARNs, queue URLs, table
  names, bucket names, account IDs, tokens, and user payloads.
- Route 53, CloudFront, and other traffic-management controls remain governed
  by separate infrastructure decisions and later validation.

## Non-Goals

This decision does not implement:

- failover
- health-based routing
- owner reassignment
- cross-region retry
- queue draining
- replay
- Route 53 or CloudFront changes
- new observability infrastructure
- a persistent regional health store
