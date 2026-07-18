# MR-009D Runtime Evidence Report

## 1. Executive Summary

MR-009D3 runtime validation was attempted on 2026-07-18 from
17:15Z to 17:25Z against the development active-active deployment at
deployment ID `3fe0077`.

The pre-validation health gate passed in both active regions, queues were
empty, worker event-source mappings were enabled, alarms were `OK`, Terraform
reported no drift, and the `us-east-2` witness remained data-only.

Synthetic business work was not created. Repository inspection and a
read-only route probe showed a blocking contract conflict: the Lambda handler
and feature tests expose the supported asynchronous workflow through
`POST /resume-upload-url` and `POST /analyze-uploaded-resume`, but the
deployed API Gateway protected route set exposes only legacy route keys such
as `POST /resume-analysis`. The needed asynchronous workflow returned
`404 Not Found` at the gateway in both active regions before authentication
or application code could run.

MR-009D remains open.

## 2. Repository Authority Reviewed

Reviewed before runtime write actions:

- `AGENTS.md`
- AI Engineering Playbook
- validation contract
- active multi-site roadmap
- Codex working context
- accepted decisions `MS-001` through `MS-008`
- MR-009D runtime-validation plan
- MR-009D discovery report
- MR-009D deployment report
- deployment runbook
- operational runbook
- API routes, request context, idempotency, placement, outbox, transport,
  worker, and cleanup implementation
- Terraform outputs
- Git and worktree state

## 3. Git and Deployment State

- Branch: `main`, ahead of `origin/main` by 9 commits.
- Top commits present:
  - `3fe0077 fix: permit API readiness dependency checks`
  - `35c722f fix: attach PDF dependency layer to regional APIs`
- Dirty state before evidence documentation: MR-009D docs plus generated
  `build/`.
- Terraform workspace: `default`.
- Terraform state: populated with active east/west regional runtime,
  shared identity, MRSC table, alarms, dashboard, queues, and event-source
  mappings.
- Terraform outputs: east and west deployment IDs were `3fe0077`; active
  regions were `us-east-1` and `us-west-2`; witness was `us-east-2`.
- No Terraform change was needed. No-drift plan with explicit development
  variables returned exit code 0 and `No changes`.

## 4. Pre-Validation Health Results

Health gate timestamp: `2026-07-18T17:15:50Z`.

| Region | Endpoint | HTTP | Latency | Status | Site | Role | Env | Deployment |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |
| `us-east-1` | `/health/live` | 200 | 1.373s | `alive` | `east` | `active` | `dev` | `3fe0077` |
| `us-east-1` | `/health/ready` | 200 | 1.664s | `ready` | `east` | `active` | `dev` | `3fe0077` |
| `us-west-2` | `/health/live` | 200 | 1.235s | `alive` | `west` | `active` | `dev` | `3fe0077` |
| `us-west-2` | `/health/ready` | 200 | 1.747s | `ready` | `west` | `active` | `dev` | `3fe0077` |

Readiness in both regions reported:

- `regionalHealth.scope`: `readiness`
- classification: `HEALTHY`
- reason code: `ALL_REQUIRED_CHECKS_PASS`
- observations: configuration, DynamoDB, and SQS all `pass`
- observation freshness: `fresh=true`, `freshnessSeconds=60`

The pre-validation health gate passed.

## 5. Queue Baseline

Both active regions had empty processing queues and DLQs before any synthetic
business work was attempted.

| Region | Queue | Visible | In Flight | Delayed | DLQ Visible |
| --- | --- | ---: | ---: | ---: | ---: |
| `us-east-1` | `processing_queue` | 0 | 0 | 0 | 0 |
| `us-west-2` | `processing_queue` | 0 | 0 | 0 | 0 |

Additional read-only evidence:

- processing queues use a 180 second visibility timeout.
- redrive policy max receive count is 5.
- SQS-managed encryption is enabled.
- both worker event-source mappings are `Enabled`.
- both event-source mappings use batch size 5 and
  `ReportBatchItemFailures`.

No SQS messages were received, deleted, sent, purged, or redriven.

## 6. Synthetic Data Definition

Planned validation-run identifier format:

```text
MR009D3-<UTC timestamp>
```

Planned synthetic resume and job text were non-sensitive and development-only.
No synthetic business data was submitted because the deployed API route
contract blocked the supported asynchronous workflow before application
execution.

## 7. Authentication and Principal

The supported API uses Cognito JWT authorization on protected routes. A
business API principal was not created because the required async route did
not exist at API Gateway. A protected-route probe against an existing route
returned `401 Unauthorized`, while the needed async helper route returned
`404 Not Found`, proving route reachability was the immediate blocker rather
than token acquisition.

No password, access token, refresh token, ID token, or session secret was
created or recorded.

## 8. Workflow Selected

Repository-supported smallest asynchronous workflow:

```text
PUT /target-career
POST /resume-upload-url
PUT synthetic PDF through returned presigned URL
POST /analyze-uploaded-resume
GET /analysis/{id}
DELETE /analysis/{id}?version=<version>
```

This workflow would prove API request context, durable work creation, outbox
creation, outbox publishing, SQS transport, worker processing, final state,
status retrieval, and cleanup.

The deployed API Gateway did not expose `POST /resume-upload-url` or
`POST /analyze-uploaded-resume`, so the workflow could not be invoked through
normal application APIs.

## 9. Placement Algorithm Assessment

Current repository behavior:

- `RequestContext.region` comes from regional runtime configuration.
- New idempotency reservations default `ownerRegion` to the current region
  unless a caller passes an explicit owner region inside application code.
- Current resume-analysis API handlers do not accept or pass a supported
  caller-supplied owner-region field.
- Outbox events default `ownerRegion` to `createdRegion`.
- Placement evaluation can identify local or non-local placement when a
  persisted or message owner region is present.
- Health state does not select ownership and does not alter transport.

Implication: even after the route blocker is fixed, normal business API calls
can currently create local owner-region work only. A supported mechanism for
creating remote-owned work through normal APIs is not present in the inspected
repository. Direct DynamoDB writes, outbox mutation, SQS sends, or manual
ownership changes were not authorized and were not used.

## 10. Test Cases Selected

Achievable without violating repository contracts:

- east-initiated local flow: blocked by deployed route contract.
- west-initiated local flow: blocked by deployed route contract.

Not currently achievable through supported business APIs:

- east-initiated work owned by west.
- west-initiated work owned by east.

## 11. East Local-Flow Evidence

Not created. The east deployed gateway returned `404 Not Found` for
`POST /resume-upload-url`, while an existing protected route returned
`401 Unauthorized`. No synthetic work item was created.

## 12. West Local-Flow Evidence

Not created. The west deployed gateway returned `404 Not Found` for
`POST /resume-upload-url`, while an existing protected route returned
`401 Unauthorized`. No synthetic work item was created.

## 13. East-to-West Cross-Region Evidence

Not created. Cross-region ownership is not currently selectable through the
supported business API contract.

## 14. West-to-East Cross-Region Evidence

Not created. Cross-region ownership is not currently selectable through the
supported business API contract.

## 15. Ownership Evidence

Repository inspection confirms newly created idempotency, work, and outbox
records carry `ownerRegion`, defaulting to the current runtime region for new
business API work. Runtime evidence for newly created synthetic records was
not collected because no records were created.

## 16. Outbox Evidence

Repository inspection confirms uploaded-resume analysis creates a transactional
outbox item with `eventType=RESUME_ANALYSIS_REQUESTED` and `status=PENDING`.
Runtime outbox evidence was not collected because no synthetic work was
created.

## 17. Transport Evidence

Repository inspection confirms the outbox publisher sends local placement to
the local processing queue and non-local placement to the owner-region queue.
Runtime transport evidence was not collected because no synthetic outbox item
was created.

## 18. Worker Evidence

Both regional worker event-source mappings are enabled, batch size 5, with
partial-batch failure reporting. Runtime worker invocation evidence for
synthetic work was not collected because no synthetic message was delivered.

## 19. Final State Evidence

No synthetic work item reached a final durable state because no synthetic work
item was created.

## 20. DynamoDB Synthetic-Record Evidence

No synthetic DynamoDB business, idempotency, outbox, or result records were
created. No DynamoDB business item was read. No table scan was performed.

The active-region DynamoDB table description reported:

- table status: `ACTIVE`
- multi-region consistency: `STRONG`
- active west replica: `ACTIVE`
- witness region: `us-east-2`, witness status `ACTIVE`
- item count: 0 at observation time

## 21. End-to-End Correlation Reconstruction

Not available. No synthetic request, work ID, outbox event ID, transport
message ID, or worker runtime invocation ID was produced.

## 22. Idempotency Same-Payload Result

Not executed. The required business API route was unavailable at API Gateway.

## 23. Idempotency Conflicting-Payload Result

Not executed. The required business API route was unavailable at API Gateway.

## 24. Queue and DLQ After-State

Because no synthetic business work was created, after-state matched baseline:
both processing queues and both DLQs remained empty at the read-only checks.

## 25. Metrics and Alarm Evidence

Read-only CloudWatch alarm inspection showed 11 east alarms and 11 west alarms
in `OK`. All inspected alarms had empty alarm actions and
`treat_missing_data=notBreaching`.

Expected activity from synthetic business work was not present because no
synthetic work was created.

## 26. Dashboard Evidence

Terraform output confirms the operations dashboard is enabled and includes
API, Lambda, queue, DLQ, worker/outbox failure, throttle, and DynamoDB
coverage for east and west. Runtime visual dashboard inspection was not
performed during this incomplete validation.

## 27. Witness Evidence

Read-only witness checks showed:

- no witness-region Lambda functions in the queried runtime inventory.
- no witness-region API Gateway APIs in the queried runtime inventory.
- no witness-region processing queues for the project development prefix.
- no witness-region active-region alarm set for the project development
  prefix.
- active-region DynamoDB description reports the `us-east-2` witness as
  `ACTIVE`.

No workload was sent to the witness.

## 28. Cleanup Results

No synthetic principal, token file, request file, upload object, work record,
idempotency record, outbox event, queue message, or result record was created.
There was nothing to clean up.

Temporary local response files under `/tmp/mr009d3-*` were diagnostic only and
contained no credentials.

## 29. Evidence Limitations

Blocking limitations:

- Deployed API Gateway routes do not expose the repository-supported
  asynchronous resume upload and uploaded-analysis endpoints.
- Current normal business API behavior does not provide a supported way to
  select a remote owner region, so cross-region owner-placement cases cannot
  be generated without an additional accepted mechanism.

Non-blocking evidence collected:

- health gate passed.
- queue baseline was empty.
- worker event-source mappings were enabled.
- alarms were `OK`.
- witness remained data-only.
- Terraform no-drift plan passed.

## MR-009D3A Reachability and Placement-Testability Update

MR-009D3A addresses the two blocking prerequisites identified above. It does
not create synthetic business work and does not complete MR-009D.

Selected route-contract approach:

- shared source-level route inventory in `src/core/api_contract.py`;
- handler route registration asserts that its routes match that inventory;
- Python tests compare API Gateway Terraform route declarations with the
  authoritative protected and public route sets;
- Terraform tests assert both active regions expose the same protected route
  set, expose health publicly, and reject obsolete legacy route keys.

Legacy route disposition:

- `POST /resume-analysis`: obsolete infrastructure-only route, removed.
- `POST /job-matching`: obsolete infrastructure-only route, removed.
- `GET /job-matching`: obsolete infrastructure-only route, removed.
- `DELETE /job-matching/{matchId}`: obsolete infrastructure-only route,
  removed.
- `POST /resume-tailoring`: obsolete infrastructure-only route, removed.

Selected remote-ownership mechanism:

- development-only `X-Validation-Owner-Region` header on initial
  `POST /analyze-uploaded-resume`;
- disabled by default;
- deployable only in `dev` when explicitly enabled;
- requires Cognito authentication and the
  `synthetic-runtime-validation` group claim;
- validates requested owners against configured active regions;
- rejects `us-east-2` witness ownership;
- records `syntheticPlacementOverrideUsed`;
- includes owner region and override use in the uploaded-resume idempotency
  fingerprint;
- does not mutate existing ownership and does not use health state as routing
  or placement authority.

MR-009D3B may begin only after MR-009D3A deployment verifies that both regions
return authorization responses rather than `404` for
`POST /resume-upload-url` and `POST /analyze-uploaded-resume`, health remains
green, the validation group/config is present, and Terraform reports no drift.

## 30. Documentation Created or Updated

Created:

- `docs/operations/platform-v2/MR-009D_RUNTIME_EVIDENCE_REPORT.md`

Updated:

- `docs/engineering/MULTI_SITE_COMPLETION_PLAN.md`
- `docs/operations/platform-v2/MR-009D_RUNTIME_VALIDATION_PLAN.md`
- `docs/operations/platform-v2/MR-009D_DEPLOYMENT_REPORT.md`

## 31. Final Repository Validation

Final validation was limited to documentation-safe checks because MR-009D3 did
not pass and no code or Terraform source was intentionally changed.

Completed:

- `git diff --check`: passed before documentation edits.
- Terraform no-drift plan with explicit development variables: passed,
  exit code 0, no changes.

Not run after documentation edits:

- full Python tests
- Lambda package rebuild and artifact validation
- Terraform static validation and focused Terraform tests
- platform foundation validation

## 32. Commit Created, if Applicable

No commit was created because MR-009D runtime validation is not complete.

## 33. Commit Hash and Subject

Not applicable.

## 34. Repository Status

MR-009D documentation remains modified/untracked locally. Generated build
artifacts remain untracked and must not be committed as MR-009D evidence.

## 35. MR-009D Completion Assessment

MR-009D is not complete. The deployment prerequisite is still healthy, but
synthetic asynchronous runtime behavior was not proven.

Required missing evidence:

- synthetic business work accepted by both active regional APIs.
- local outbox, queue, worker, and final-state evidence in both regions.
- cross-region owner-region transport and worker evidence.
- runtime idempotency same-payload and conflict behavior.
- end-to-end correlation reconstruction for local and cross-region flows.

## 36. MR-010 Entry Recommendation

Do not start MR-010. Before MR-009D can close, MR-009D3B must use the
corrected route contract and approved development validation override to prove
local and cross-region asynchronous processing, idempotency, correlation,
monitoring, cleanup, and witness boundaries in the deployed development
runtime.

MR-010 still requires a failover/recovery decision record and failure-mode
review before implementation.

## 37. Runtime Validation Decision

RUNTIME VALIDATION NOT COMPLETE

## Required Confirmations

- Only AWS profile `mpopsaws-ai-resume-coach-mike` was used.
- The target remained development.
- No profile, role, workspace, backend, or default region changed.
- No Terraform apply occurred.
- No infrastructure or application deployment occurred.
- No Terraform import occurred.
- No Terraform state was manually edited.
- No production or staging resource was accessed.
- Only synthetic non-sensitive data was planned.
- No real resume, job, user, or customer data was used.
- No unrelated DynamoDB item was read.
- No table scan occurred.
- No arbitrary SQS message was received or deleted.
- No SQS message was manually sent.
- No queue was purged.
- No DLQ was redriven.
- No ownership record was manually changed.
- No outbox record was manually changed.
- No processing state was manually reset.
- No failover occurred.
- No traffic shifting occurred.
- No replay occurred.
- No transport retry was introduced.
- No queue draining occurred.
- No regional fencing occurred.
- No automatic recovery was introduced.
- Health remained diagnostic and readiness-scoped.
- Health state did not become routing authority.
- Witness responsibilities remained unchanged.
- No workload was sent to the witness.
- No secret, password, or token was recorded.
- No temporary token files were created.
- Generated build artifacts were not committed.
- MR-010 was not started.
- Architecture posters were not regenerated.
- Human engineering ownership remained explicit.
