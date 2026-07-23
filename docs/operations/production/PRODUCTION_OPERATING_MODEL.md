# Production Operating Model

## Purpose

This operating model defines how the AI Resume Coach should be operated after release. It connects the implemented multi-site controls to clear ownership, release practices, health review, incident response, capacity management, and evidence retention.

## Production roles

For a portfolio deployment, one person may perform several roles, but the responsibilities remain distinct.

| Role | Responsibilities |
|---|---|
| Service owner | Customer outcomes, priorities, service objectives, risk acceptance, and release decisions |
| On-call operator | Alert triage, incident coordination, safe restoration, and evidence capture |
| Platform engineer | AWS infrastructure, regional health, deployment tooling, observability, and capacity |
| Application engineer | API, workflow, provider, idempotency, and business-state diagnosis |
| Security owner | Identity, WAF, audit evidence, secrets, vulnerability response, and access review |

## Daily operating review

Review the following at least once per operating day when the service is actively used:

1. Synthetic success for both active sites.
2. API request volume, 4XX, 5XX, and p95 latency by region.
3. Lambda errors, throttles, invocation volume, and p95 duration.
4. Queue depth, oldest-message age, messages submitted, and messages deleted.
5. Worker-record and outbox-publish failures.
6. DLQ depth.
7. DynamoDB throttles and consumed capacity.
8. Recent east and west application errors.
9. Deployment ID and any changes made since the prior review.

A low-volume portfolio service may have long periods with no traffic. Missing traffic is not proof of health; synthetics and direct readiness checks remain the heartbeat controls.

## Release management

A production release should require:

- a clean repository and reviewed change set;
- application tests and Terraform contract tests passing;
- an inspected Terraform plan;
- an identified rollback point;
- a deployment ID tied to the source revision;
- direct east and west health verification;
- global endpoint verification;
- dashboard and alarm review after deployment;
- a short release record with outcome and anomalies.

Avoid combining a major application change, infrastructure topology change, and operational-control change in one release unless the change cannot be safely decomposed.

## Change windows

Use a planned change window for:

- routing policy or health-check changes;
- DynamoDB replica or witness changes;
- queue, event-source mapping, or retry-policy changes;
- identity or WAF changes;
- alarm threshold changes;
- provider changes that can alter latency, cost, or output behavior.

Routine static-frontend content changes may use a lighter process when rollback remains immediate and no API contract changes are included.

## Capacity and cost review

Review monthly, or after a meaningful traffic increase:

- API request growth and regional distribution;
- worker throughput versus queue age;
- Lambda duration and concurrency pressure;
- DynamoDB read/write consumption and throttles;
- S3 storage and data-transfer growth;
- CloudWatch log, metric, dashboard, alarm, synthetic, and retention costs;
- AI-provider request volume, latency, failures, and spend when enabled.

The current on-demand architecture should be governed by trends and guardrails rather than pre-allocated capacity targets.

## Backup and recovery

The platform's multi-site design improves regional resilience but is not a substitute for backup and restore. Production operation should separately define:

- DynamoDB point-in-time recovery and restore testing;
- S3 versioning or recovery policy for uploaded documents;
- infrastructure-state backup and recovery;
- Cognito recovery and administrator-access procedures;
- evidence-retention and deletion requirements.

No recovery procedure may mutate `ownerRegion`, silently move queue messages between regions, or treat infrastructure rollback as data rollback.

## Security operations

At minimum:

- enable the approved WAF controls for production;
- review privileged IAM access regularly;
- keep secrets outside source control and evidence bundles;
- monitor authentication and authorization failures without logging tokens;
- review dependencies and Lambda layers for vulnerabilities;
- retain only the minimum operational evidence required;
- test incident access before it is needed.

## Quarterly resilience exercise

Run a planned exercise that covers:

- one routing-isolation scenario;
- one worker interruption and backlog recovery;
- one DLQ investigation tabletop;
- one restore-from-backup tabletop or test;
- verification that runbooks, commands, outputs, and contacts are still current.

The MR-014 certification remains the implementation baseline; quarterly exercises demonstrate that the operating capability has not drifted.
