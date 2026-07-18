# MR-007I — Observability Foundation

## Problem statement

Platform V2 can be deployed across two active Regions, but deployment alone does
not make it operable. Engineers need a consistent way to determine whether the
platform is healthy, identify which Region or subsystem is degraded, correlate
events across asynchronous workflows, and distinguish customer-impacting
failures from internal noise.

## Goals

- Establish one platform-wide telemetry language.
- Correlate requests, workflows, deployments, Regions, and architecture versions.
- Expose both active Regions through one operational dashboard.
- Create a curated, actionable alarm set.
- Enable distributed tracing without making it a mandatory recurring expense.
- Validate public health endpoints from outside the application runtime.
- Treat privacy and telemetry cost as architecture concerns.

## Non-goals

- Introduce a third-party observability platform.
- Store resume text, JWTs, passwords, API keys, or access tokens in logs.
- Create dozens of low-value alarms.
- Claim native API Gateway HTTP API X-Ray stage tracing.
- Monitor DynamoDB MREC replication latency; Platform V2 uses MRSC.
- Define final incident-response and disaster-recovery procedures. Those belong
  to MR-007J.

## Success criteria

1. Every regional workload receives the same structured logging contract.
2. Request IDs, correlation IDs, and deployment IDs remain distinct.
3. Lambda tracing can be enabled symmetrically in both Regions.
4. One dashboard provides API, Lambda, queue, worker/outbox failure, data,
   synthetic, and log views.
5. Eleven curated alarms can be enabled per Region.
6. One canary per Region validates `/health`, `/health/live`, and `/health/ready`.
7. Cost-bearing capabilities are disabled until explicitly selected.
8. Sensitive and high-volume customer content is prohibited from logs.

## Architecture decisions and tradeoffs

### Structured JSON over plain text

Selected because it is machine-queryable, portable, and supports stable
operational fields. The tradeoff is that application code must follow the schema
rather than emitting arbitrary strings.

### Request ID and correlation ID are separate

A request ID identifies one invocation. A correlation ID identifies the broader
workflow, including API, outbox, queue, and worker activity. Reusing one field
for both would make asynchronous investigation ambiguous.

### CloudWatch is the default platform

CloudWatch is already integrated with the AWS services used by Platform V2 and
avoids another vendor and data pipeline. This is intentionally a portfolio-scale
choice; a larger organization might export telemetry to a centralized platform.

### Curated alarms over exhaustive alarms

The alarm set focuses on availability, latency, Lambda errors, queue health,
dead-letter messages, DynamoDB throttling, sustained worker record failures,
and sustained outbox publishing failures. Fewer actionable alarms are more
valuable than a large, noisy catalog.

### Lambda X-Ray is cost-gated

Lambda functions support active X-Ray tracing. The platform exposes and tests
the capability but leaves it disabled by default to avoid unnecessary trace
ingestion costs.

### HTTP API tracing limitation is explicit

Platform V2 retains API Gateway HTTP APIs for cost and simplicity. Native API
Gateway stage X-Ray tracing is not modeled as supported; tracing begins in the
Lambda integration and is correlated with API access-log request IDs.

### Synthetic monitoring is regional and batched

One canary in each active Region checks all three public health endpoints in a
single run. This gives an external availability perspective while reducing the
number of chargeable canary runs.

### MRSC metrics differ from MREC metrics

The platform does not create a `ReplicationLatency` alarm. AWS documents that
metric for multi-Region eventual consistency. Platform V2 uses multi-Region
strong consistency, so its data alarms focus on throttling and service health.

## Telemetry schema

Required fields:

```json
{
  "timestamp": "ISO-8601",
  "level": "INFO",
  "service": "resume-analysis",
  "component": "api",
  "operation": "POST /resume-analysis",
  "requestId": "one invocation",
  "correlationId": "end-to-end workflow",
  "deploymentId": "deployed artifact",
  "region": "us-east-1",
  "site": "east",
  "userId": "stable opaque identifier or null",
  "tenantId": null,
  "durationMs": 37,
  "result": "SUCCESS",
  "errorCode": null,
  "architectureVersion": "PlatformV2"
}
```

`x-correlation-id` is the propagation header. When a caller does not provide
one, the application creates it and propagates it to outbox items and queue
messages.

## Privacy rules

Never log:

- authorization headers;
- JWT access or refresh tokens;
- passwords;
- API keys;
- raw resume text;
- full uploaded-document content.

Prefer opaque user IDs over email addresses. Error messages must be sanitized
before they are logged.

## Metrics strategy

AWS service metrics remain in their native namespaces. Custom application and
business metrics use:

```text
AIResumeCoach/Platform
```

Recommended dimensions are deliberately low-cardinality:

- Environment
- Region
- Site
- Service
- Operation
- Result

Do not use user IDs, request IDs, correlation IDs, email addresses, job URLs, or
document IDs as metric dimensions.

## Dashboard scope

The shared operations dashboard contains:

- regional API request and 5XX views;
- regional API p95 latency;
- Lambda errors;
- SQS queue depth and oldest-message age;
- DynamoDB throttling;
- synthetic health success;
- a Logs Insights error view.

The namespace also reserves space for product metrics such as resume analyses,
job matches, and resume tailoring completions. Application instrumentation will
publish those metrics during migration to Platform V2.

## Alarm catalog

Per active Region:

1. HTTP API 5XX
2. HTTP API p95 latency
3. API Lambda errors
4. Worker Lambda errors
5. Outbox-publisher Lambda errors
6. Processing-queue oldest message
7. Processing-queue visible depth
8. Dead-letter queue messages
9. DynamoDB throttled requests

Alarm actions are optional and externalized. MR-007J will define notification,
escalation, incident ownership, and response procedures.

## Cost controls

The structured logging contract is enabled by default. These resource-bearing
capabilities are disabled by default:

```hcl
enable_active_tracing          = false
enable_observability_dashboard = false
enable_operational_alarms      = false
enable_synthetic_monitoring    = false
```

Synthetic monitoring defaults to one batched run every five minutes per Region
and seven-day artifact retention when enabled.
