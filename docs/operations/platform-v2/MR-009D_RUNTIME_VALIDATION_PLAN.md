# MR-009D Runtime Validation Plan

## Status

Plan plus attempted MR-009D3 execution. Deployed health, queue, monitoring,
witness, and no-drift evidence was collected on 2026-07-18, but synthetic
business work was not created because the deployed API Gateway route contract
does not expose the repository-supported asynchronous upload-analysis
workflow. The evidence and blocker are recorded in
`docs/operations/platform-v2/MR-009D_RUNTIME_EVIDENCE_REPORT.md`.

MR-009D validates the multi-site runtime after a separately approved
deployment. It must not deploy infrastructure, create application data, mutate
queues, redrive DLQs, change routing, or alter ownership without explicit
human authorization for the target environment.

## Scope

Original milestone commit:

```text
9c9c28e feat: complete active-active routing, transport, traceability, and health foundation
```

Current deployed repair commit:

```text
3fe0077 fix: permit API readiness dependency checks
```

Active application regions:

- `us-east-1`
- `us-west-2`

Witness region:

- `us-east-2`

The validation proves deployed behavior only. Terraform tests and local unit
tests remain necessary preconditions, but they are not runtime evidence.

## Authorization Gate

Before any external write action, deployment, Terraform apply, API invocation
that creates work, or cleanup action, the operator must record:

- target AWS account alias or other non-sensitive account identifier;
- target environment;
- approved active regions;
- witness region;
- expected deployment ID;
- approved deployment workflow;
- approved Terraform workspace and state backend;
- approved AWS identity, profile, or role;
- permission to deploy, if deployment is required;
- permission to create safe smoke-test records;
- permission to invoke regional application APIs;
- permission to inspect logs, queues, alarms, dashboards, and DynamoDB;
- acceptable test-data classification;
- cleanup obligations and retained-evidence policy.

Do not infer authorization from a locally configured AWS profile. Do not switch
accounts, roles, profiles, regions, workspaces, or backends implicitly.

If authorization is incomplete, stop before runtime writes and produce a
validation-readiness report instead of a completed evidence report.

## Pre-Deployment Validation

Run from the repository root before any authorized deployment:

```bash
python -m compileall src tests
pytest -q tests
cd infra
terraform fmt -recursive -check
terraform validate
terraform test -filter=tests/observability.tftest.hcl
terraform test -filter=tests/regional_compute.tftest.hcl
terraform test -filter=tests/regional_api_gateway.tftest.hcl
terraform test -filter=tests/resume_analysis_mrsc.tftest.hcl
cd ..
./tools/validate_platform_v2_foundation.sh
git diff --check
```

Also run focused tests for regional transport, outbox publishing, correlation,
runtime identity, regional health, readiness timeout behavior, idempotency, and
worker processing when those tests changed or when local validation is stale.

Do not proceed to deployment with failing validation.

## Existing Deployment Assessment

Use approved read-only mechanisms to classify the target environment as:

- fully current;
- partially current;
- older than commit `9c9c28e`;
- inconsistent between active regions;
- unable to determine.

Inspect, without recording sensitive values:

- Lambda versions or code hashes for API, worker, and outbox publisher;
- regional API Gateway stages and direct endpoints;
- safe Lambda environment configuration;
- DynamoDB global-table replicas and witness status;
- regional SQS queues, DLQs, policies, and event-source mappings;
- CloudWatch log groups;
- CloudWatch alarms and dashboard widgets;
- Terraform outputs;
- deployment IDs.

Do not claim runtime validation against a partially updated environment unless
the difference is explicitly recorded and non-blocking.

MR-009D3 route-contract finding:

- application handler routes include `POST /resume-upload-url` and
  `POST /analyze-uploaded-resume`;
- feature tests exercise those same routes;
- Terraform and deployed API Gateway protected routes expose legacy route keys
  such as `POST /resume-analysis` instead;
- route probes returned `404 Not Found` for `POST /resume-upload-url` in both
  active regions while an existing protected route returned `401 Unauthorized`;
- therefore no synthetic business write was attempted.

MR-009D3A remediation requirements:

- regional API Gateways must expose the repository-supported protected product
  route contract, including `POST /resume-upload-url` and
  `POST /analyze-uploaded-resume`;
- obsolete infrastructure-only route keys such as `POST /resume-analysis`,
  `POST /job-matching`, `GET /job-matching`,
  `DELETE /job-matching/{matchId}`, and `POST /resume-tailoring` must not be
  retained as undocumented compatibility aliases;
- automated Python and Terraform tests must compare handler routes with
  deployed API Gateway route declarations, not only east/west symmetry;
- remote-owned synthetic work for MR-009D3B must be created only through the
  development-only validation owner override documented in
  `docs/architecture/decisions/MS-009_DEVELOPMENT_SYNTHETIC_PLACEMENT_OVERRIDE.md`.

## Safe Test Data

Use only synthetic, non-sensitive data:

```text
MR-009D synthetic runtime validation record.
No personal or production data.
Safe to delete after validation.
```

Do not use real resume text, personal data, customer data, secrets,
proprietary job descriptions, or production user content.

Record for each synthetic work item:

- test timestamp in UTC;
- environment;
- initiating region;
- expected owner region;
- request ID;
- correlation ID;
- work ID;
- outbox event ID;
- transport message ID, when available;
- deployment ID;
- cleanup status.

## Runtime Evidence Steps

### 1. Active-Region Identity

Invoke `/health/live` directly in each active region and capture:

- endpoint invoked;
- HTTP status;
- response timestamp;
- response latency;
- region;
- site name;
- region role;
- environment;
- deployment ID.

Confirm liveness remains dependency-free and does not imply readiness.

### 2. Readiness

Invoke `/health/ready` directly in each active region and capture:

- HTTP status;
- readiness result;
- `regionalHealth.scope`;
- readiness classification;
- bounded reason code;
- evaluation timestamp;
- observation timestamps and freshness;
- configuration, persistence, and processing observation results;
- response latency.

Confirm responses expose no secrets, account IDs, ARNs, table names, queue
URLs, bucket names, raw exception text, tokens, or user payloads.

### 3. Regional API Invocation

Invoke safe supported API operations independently through both regional API
endpoints. Capture:

- initiating region;
- endpoint;
- HTTP status;
- request ID;
- correlation ID;
- created work ID;
- expected owner region;
- placement decision, if exposed in safe diagnostics;
- deployment ID;
- sanitized response evidence.

Do not use the global endpoint when proving independent regional behavior.

### 4. Ownership and Placement

Inspect persisted records through approved tooling and confirm:

- `ownerRegion` is persisted;
- ownership is deterministic and not inferred from health;
- source region is recorded where required;
- request and correlation identifiers are present;
- duplicate requests preserve accepted idempotency behavior;
- retries or continuation do not overwrite ownership.

Do not manually mutate ownership or outbox records.

### 5. Local Transport

For a work item owned by the initiating region, prove:

```text
regional API -> persisted work -> outbox item -> local queue -> local worker
  -> final work state
```

Capture API, work, outbox, queue, worker, final-state, and correlation
evidence. Confirm no cross-region transport is used unnecessarily.

### 6. Cross-Region Transport

For a work item initiated in one active region and owned by the other active
region, prove:

```text
source-region API -> shared persisted work -> source-region outbox
  -> owner-region queue -> owner-region worker -> final work state
```

Capture source-region publisher logs, target queue evidence, transport message
ID, owner-region worker logs, and final persisted state.

If accepted placement rules do not naturally produce a cross-region case, do
not bypass application invariants. Record the approved test mechanism required.

For development runtime validation, the approved mechanism is
`X-Validation-Owner-Region` on `POST /analyze-uploaded-resume`, subject to the
MS-009 controls. It must be used only with an authenticated synthetic
development principal that has the configured validation group claim. It must
not be invoked without MR-009D3B authorization.

### 7. Worker Runtime

For each work item, capture safe worker evidence:

- Lambda function name;
- AWS region;
- owner region;
- source region;
- current region;
- deployment ID;
- runtime invocation ID;
- request ID;
- correlation ID;
- work ID;
- outbox event ID;
- transport message ID;
- job type;
- processing result.

Runtime invocation ID remains diagnostic only.

### 8. End-to-End Correlation

For at least one local flow and one cross-region flow when safely possible,
construct a chronological evidence chain:

```text
API request
-> request context
-> work creation
-> ownership and placement
-> outbox creation
-> outbox dispatch
-> transport message
-> queue receipt
-> worker invocation
-> processing result
-> persisted final state
```

Use canonical identifiers: `requestId`, `correlationId`, `workId`,
`outboxEventId`, `transportMessageId`, and `runtimeInvocationId`.

### 9. Idempotency

Validate duplicate behavior with safe requests:

- same request identifier and same payload;
- same request identifier with conflicting payload, if supported safely;
- duplicate SQS or outbox behavior only when naturally observable or validated
  in a lower environment.

Confirm duplicate handling preserves business behavior and does not imply
exactly-once transport.

### 10. Queue and Event Sources

For each active region, inspect:

- processing queue;
- DLQ;
- event-source mapping;
- batch size;
- partial-batch response configuration;
- queue visibility timeout;
- Lambda timeout;
- queue encryption;
- queue policy;
- approximate queue depth;
- oldest-message age.

Do not purge queues or redrive DLQs.

### 11. DynamoDB and Witness

Inspect the global-table topology and confirm:

- active replicas are in `us-east-1` and `us-west-2`;
- witness region is `us-east-2`;
- witness remains limited to the MRSC data role;
- no application API, worker, queue, or transport path is deployed in the
  witness;
- runtime does not route work to the witness.

### 12. Observability

For each active region, verify:

- API 5xx alarm;
- API latency alarm;
- API Lambda error alarm;
- worker Lambda error alarm;
- outbox publisher Lambda error alarm;
- queue-depth alarm;
- oldest-message-age alarm;
- DLQ alarm;
- DynamoDB throttling alarm;
- worker-record-failure alarm;
- outbox-publish-failure alarm.

Confirm dashboard widgets show API, Lambda, queue, DLQ, custom worker/outbox,
and DynamoDB signals for both active regions. Confirm high-cardinality
identifiers remain log fields only.

## Cleanup

Cleanup must use only approved mechanisms:

- supported application delete or cleanup APIs, if available;
- existing repository-supported operational tooling;
- accepted TTL behavior;
- documented retention of synthetic records as evidence.

Do not directly delete shared records, purge queues, redrive DLQs, alter
ownership, reset outbox state, or remove CloudWatch evidence needed for the
report.

Record every synthetic record left behind.

## Evidence Report Template

Create the completed evidence report only after authorized runtime validation.
Use this structure:

```text
Validation date/time UTC:
Commit validated:
Target account alias or non-sensitive identifier:
Environment:
Active regions:
Witness region:
Expected deployment ID:
Observed deployment IDs:
Validation operator:
Authorization scope:
Deployment state:
Runtime evidence summary:
Local-flow evidence:
Cross-region-flow evidence:
Idempotency evidence:
Queue and event-source evidence:
DynamoDB and witness evidence:
Observability evidence:
Discrepancies:
Evidence limitations:
Cleanup status:
Readiness decision:
```

Do not include account numbers, credentials, tokens, queue URLs, sensitive ARNs,
private resume content, user data, or full raw logs.

MR-009D3B entry criteria after MR-009D3A:

- both active regional APIs return authorization responses, not `404`, for
  `POST /resume-upload-url` and `POST /analyze-uploaded-resume` without a
  token;
- both active regional APIs expose identical protected route sets;
- health routes remain public and healthy;
- validation placement override is explicitly enabled only in development;
- the dedicated validation Cognito group exists;
- the witness region cannot be selected as owner;
- default ownership remains ingress-local when no validation header is used;
- idempotency fingerprints include owner region for uploaded-resume analysis;
- Terraform reports no drift.
- the outbox publisher can run through an accepted normal trigger, or another
  repository-approved validation dispatch mechanism exists that does not use
  manual SQS sends, direct outbox mutation, replay, retry, failover, traffic
  shifting, queue draining, or worker requeueing.

MR-009D3C selects the normal EventBridge schedule as the accepted trigger.
Before retrying synthetic business work, verify:

- `enable_outbox_publisher_schedule=true` is explicitly set for the
  development deployment;
- east and west schedules are `ENABLED`;
- both publishers have invoked through EventBridge with an empty outbox;
- empty invocations report zero examined, claimed, published, failed, skipped,
  and permanently failed records;
- queues and DLQs remain empty;
- publisher failure alarms remain `OK`;
- Terraform reports no drift with the same explicit schedule setting.

MR-009D3C observation update: deployment ID `3cdb262` corrected the publisher
handler setting and proved that EventBridge invokes both regional publishers,
but each empty scheduled invocation failed before querying any outbox records
successfully because the deployed table does not have the repository-required
`gsi1` index. The schedule was disabled again with
`enable_outbox_publisher_schedule=false` to stop recurring failures. MR-009D3B
must not restart until the DynamoDB table/index contract is explicitly
remediated and empty publisher cycles complete with zero counts.

MR-009D3D prerequisite update: the accepted remediation is to add sparse
`gsi1` with string keys `gsi1pk` and `gsi1sk`, projection `ALL`, using an
in-place DynamoDB table update. Phase 1 keeps
`enable_outbox_publisher_schedule=false` until the index reaches `ACTIVE`.
Phase 2 sets `enable_outbox_publisher_schedule=true` and observes normal empty
EventBridge-triggered publisher cycles. No synthetic business work is created in
MR-009D3D.

## Decision Criteria

Use one final decision:

- `RUNTIME VALIDATION PASSED`: all required deployed evidence was collected and
  matched accepted architecture.
- `RUNTIME VALIDATION PASSED WITH LIMITATIONS`: core runtime behavior was
  proven, with explicit non-blocking gaps.
- `RUNTIME VALIDATION NOT COMPLETE`: authorization, deployment, environment
  access, or required evidence was unavailable.
- `RUNTIME VALIDATION FAILED`: observed deployed behavior contradicted accepted
  architecture or exposed an operationally material defect.

Lack of authorization is not a system failure.

## Explicit Non-Goals

MR-009D does not implement or perform:

- failover;
- traffic shifting;
- Route 53, CloudFront, Global Accelerator, or DNS changes;
- owner reassignment;
- regional fencing;
- queue draining;
- queue purging;
- DLQ redrive;
- replay;
- transport retry;
- outbox-state mutation;
- recovery orchestration;
- health-state persistence;
- health-informed routing;
- alarm actions;
- production chaos testing;
- destructive dependency failure;
- distributed tracing;
- business feature changes;
- architecture-poster regeneration.
