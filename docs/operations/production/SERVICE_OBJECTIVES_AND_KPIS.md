# Service Objectives and KPI Catalog

## Objective

The dashboard should answer four different questions:

1. Is the service reachable and correct?
2. Is asynchronous work progressing?
3. How much is the product being used?
4. Is usage creating capacity, cost, or customer-experience risk?

The original dashboard answered the first two well. The expanded dashboard adds stronger traffic, throughput, latency, capacity, and regional diagnostic coverage. True product KPIs still require bounded application telemetry.

## Initial service-level indicators

These are proposed operating targets, not contractual commitments.

| Area | Indicator | Initial internal target |
|---|---|---|
| Availability | Successful synthetic health checks by active region | At least 99.5% over 30 days |
| API reliability | 5XX responses / total API requests | Less than 1% over 1 hour |
| API performance | API Gateway p95 latency | Less than 2 seconds for synchronous endpoints |
| Async freshness | Oldest processing message | Less than 5 minutes during normal load |
| Async reliability | Workflows reaching terminal success or explicit terminal failure | At least 99% excluding deliberate tests |
| Delivery integrity | DLQ visible messages | Zero under normal operation |
| Capacity | Lambda throttles and DynamoDB throttles | Zero sustained throttling |
| Recovery | Time to restore an interrupted worker and drain backlog | Measured during each exercise; trend should not regress |

Targets should be revised only after enough real traffic exists to establish a baseline.

## Dashboard metrics implemented in this overlay

The operations dashboard now includes:

- API request count, 4XX, 5XX, and p95 latency by region;
- Lambda errors, throttles, invocation volume, and p95 duration;
- queue depth, oldest-message age, messages sent, and messages deleted;
- worker-record failures and outbox-publish failures;
- DLQ depth;
- DynamoDB throttles and consumed read/write capacity;
- synthetic success;
- separate east and west recent-error queries.

These additions improve usage-level visibility without introducing new application metric dimensions or high-cardinality telemetry.

## Product and usage KPI gap

AWS-native metrics show infrastructure activity, not customer outcomes. They cannot reliably answer:

- how many users were active;
- which product capability was used;
- how many resume analyses, job matches, or tailoring workflows were submitted;
- completion and failure rates by capability;
- time from submission to customer-visible completion;
- provider usage, latency, and cost by provider mode;
- repeat usage, retention, or conversion between capabilities.

## Recommended bounded application metrics

Add these only through a reviewed telemetry slice. Dimensions must remain bounded, such as `Feature`, `Result`, `Provider`, `Region`, and `Environment`.

| Metric | Purpose | Safe dimensions |
|---|---|---|
| `FeatureRequests` | Product demand by capability | `Feature`, `Region`, `Result` |
| `WorkflowsSubmitted` | Accepted asynchronous work | `Feature`, `OwnerRegion` |
| `WorkflowsCompleted` | Successful customer outcomes | `Feature`, `OwnerRegion`, `Provider` |
| `WorkflowsTerminalFailed` | Explicit unrecoverable outcomes | `Feature`, `OwnerRegion`, `FailureCategory` |
| `WorkflowEndToEndDurationMs` | Submission-to-visible-result latency | `Feature`, `OwnerRegion`, `Provider` |
| `IdempotencyReplays` | Duplicate request protection activity | `Feature`, `OwnerRegion` |
| `ProviderRequests` | AI-provider demand | `Provider`, `Feature`, `Result` |
| `ProviderDurationMs` | Provider latency | `Provider`, `Feature`, `Result` |

Do not use user ID, request ID, correlation ID, work ID, document ID, job URL, or resume name as metric dimensions.

## Active-user measurement

Do not calculate unique active users with a CloudWatch metric dimension. Use privacy-aware aggregated logs or a dedicated analytics store and define:

- daily active authenticated users;
- weekly active authenticated users;
- new registrations;
- users completing a first analysis;
- users progressing from analysis to job matching or tailoring.

Any analytics design should specify retention, consent expectations, deletion behavior, and whether internal or synthetic users are excluded.

## Executive KPI view

A future executive dashboard should summarize:

- active users and new registrations;
- workflows submitted and completed by feature;
- completion rate and p95 end-to-end duration;
- regional traffic distribution;
- availability and error-budget consumption;
- AI-provider usage and estimated cost;
- incidents, recovery time, and unresolved DLQ work.

Keep this separate from the operator dashboard so product trends do not obscure urgent operational signals.
