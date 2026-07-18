# MS-003: Shared Processing Queue and DLQ

## Status

Accepted

## Decision

Retain generic shared infrastructure names:

```text
processing_queue
processing_dlq
```

The queue is a reusable asynchronous processing capability rather than a resource owned exclusively by Resume Analysis.

## Rationale

Compatible background workloads may share transport when they have similar operational characteristics. Typed messages can identify work such as Resume Analysis, Job Matching, or Resume Tailoring without prematurely multiplying queues.

## Consequences

- Terraform resource and output names remain capability-oriented.
- A consuming feature may use a domain-facing configuration name when it accurately describes the feature's dependency.
- Message compatibility must not be changed incidentally.
- Monitoring should still distinguish work types through safe structured dimensions or application metrics.

## Split Criteria

Create separate queues only when workloads differ materially in one or more of:

- throughput or concurrency
- latency objectives
- retry policy
- DLQ handling
- security boundary
- failure isolation
- deployment ownership
- operational ownership

Queue separation is an operational decision, not a naming preference.
