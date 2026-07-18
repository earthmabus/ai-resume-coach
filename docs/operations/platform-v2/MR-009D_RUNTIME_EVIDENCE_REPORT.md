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

## MR-009D3B Dispatch-Reachability Attempt

Validation window:

- UTC observation time: 2026-07-18 18:12.
- Commit and deployment ID: `ef79140`.
- Environment: development.
- Active regions: `us-east-1`, `us-west-2`.
- Witness region: `us-east-2`.
- AWS profile used: `mpopsaws-ai-resume-coach-mike`.

Repository and deployment gates:

- `git status`: branch `main`, ahead of `origin/main` by 10 commits.
- Latest commit: `ef79140 fix: align runtime validation reachability`.
- Worktree: clean except untracked generated `build/`.
- `git diff --check`: passed.
- Terraform workspace: `default`.
- Terraform state: populated.
- Terraform outputs: active regional deployment IDs are both `ef79140`.
- Synthetic placement override: enabled in development.
- Synthetic placement group: `synthetic-runtime-validation`.
- Selectable owner regions: `us-east-1`, `us-west-2`.
- Witness owner region: excluded.
- Sanitized Terraform no-drift plan with
  `enable_synthetic_placement_override=true`: exit code 0, no changes.

Health gate:

| Region | Endpoint | HTTP | Latency | Result |
| --- | --- | ---: | ---: | --- |
| `us-east-1` | `/health/live` | 200 | 1.619s | alive, site `east`, role `active`, deployment `ef79140` |
| `us-east-1` | `/health/ready` | 200 | 0.463s | `HEALTHY`, scope `readiness`, reason `ALL_REQUIRED_CHECKS_PASS` |
| `us-west-2` | `/health/live` | 200 | 1.353s | alive, site `west`, role `active`, deployment `ef79140` |
| `us-west-2` | `/health/ready` | 200 | 0.573s | `HEALTHY`, scope `readiness`, reason `ALL_REQUIRED_CHECKS_PASS` |

Protected route probes without authentication:

| Region | Route | HTTP | Result |
| --- | --- | ---: | --- |
| `us-east-1` | `POST /resume-upload-url` | 401 | authorization rejection, not `404` |
| `us-east-1` | `POST /analyze-uploaded-resume` | 401 | authorization rejection, not `404` |
| `us-west-2` | `POST /resume-upload-url` | 401 | authorization rejection, not `404` |
| `us-west-2` | `POST /analyze-uploaded-resume` | 401 | authorization rejection, not `404` |

Queue, worker, and alarm baseline:

| Region | Queue visible | Queue in flight | Queue delayed | DLQ visible | Worker mapping | Last processing result | Alarms |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| `us-east-1` | 0 | 0 | 0 | 0 | `Enabled`, batch size 5 | none reported | 11 `OK` |
| `us-west-2` | 0 | 0 | 0 | 0 | `Enabled`, batch size 5 | none reported | 11 `OK` |

Blocking dispatch finding:

- Both regional EventBridge outbox publisher schedules are deployed with
  `rate(1 minute)` expressions but `DISABLED` state.
- Terraform source sets
  `aws_cloudwatch_event_rule.outbox_publisher_schedule.state = "DISABLED"`.
- Terraform tests explicitly require both publisher schedules to remain
  disabled and currently fail the configuration if they are enabled.
- Repository authority therefore does not currently provide the normal
  scheduled outbox publisher path required to dispatch newly created outbox
  records to SQS.

Execution decision:

No synthetic business work was created. Creating target-career, upload,
analysis, idempotency, and outbox records while the normal publisher trigger is
disabled would be expected to leave work pending and would not prove the
accepted asynchronous runtime path. Manual Lambda invocation, direct SQS send,
outbox mutation, replay, or schedule enablement were not authorized for
MR-009D3B and would not be valid substitute evidence under the MR-009D
contract.

Evidence not collected in MR-009D3B:

- synthetic validation principal and JWT authentication evidence;
- synthetic PDF upload evidence;
- target-career setup;
- east local flow;
- west local flow;
- east-to-west flow;
- west-to-east flow;
- runtime idempotency same-payload and conflict behavior;
- witness-rejection and unauthorized-override runtime behavior;
- synthetic DynamoDB point-read evidence;
- outbox, transport, worker, and final durable-state evidence;
- end-to-end correlation reconstruction.

Cleanup:

No synthetic principal, group membership change, token file, PDF, request
payload, uploaded object, target-career record, analysis work item,
idempotency record, outbox record, queue message, or result record was created.
Temporary local health-response files were removed after recording the safe
summary above.

MR-009D remains open. MR-009D3B cannot proceed to business writes until a later
authorized remediation aligns repository authority and deployed runtime so the
outbox publisher can run through an accepted normal trigger, or the repository
defines a different accepted non-replay, non-manual dispatch mechanism for
runtime validation.

## MR-009D3C Outbox Publisher Trigger Attempt

Validation window:

- UTC observation window: 2026-07-18 18:46 to 19:16.
- Starting deployment ID: `ef79140`.
- Implementation deployment ID: `fdcc0a4`.
- Handler repair deployment ID: `3cdb262`.
- Environment: development.
- Active regions: `us-east-1`, `us-west-2`.
- Witness region: `us-east-2`.
- AWS profile used: `mpopsaws-ai-resume-coach-mike`.

Repository changes:

- Added explicit Terraform variable `enable_outbox_publisher_schedule`, default
  `false`.
- Restricted schedule enablement to development until a later production
  decision.
- Passed the setting to both regional application modules.
- Updated Terraform tests to prove default-disabled behavior,
  development-enabled behavior, matching schedule expressions, EventBridge
  targets, Lambda invoke permissions, and no witness schedule.
- Corrected the outbox publisher Lambda handler from
  `handler.lambda_handler` to `handler.handler`.
- Added Terraform output/test coverage for regional Lambda handler strings.
- Added decision record
  `docs/architecture/decisions/MS-010_OUTBOX_PUBLISHER_SCHEDULE_ACTIVATION.md`.

Publisher contract assessment:

- Normal trigger is EventBridge schedule -> same-region outbox-publisher
  Lambda -> DynamoDB `Query` for dispatchable outbox records -> conditional
  claim -> SQS send to local or owner-region processing queue -> conditional
  delivered/failure update.
- The publisher uses `Query` on `gsi1`, not table scan.
- Duplicate dispatch is guarded by conditional status/version/lease claim
  before SQS delivery.
- IAM allows scoped table/index reads and updates plus active-region SQS
  send/get-url; no SQS receive/delete or DynamoDB scan permission is required.
- Witness has no schedule, API, queue, DLQ, worker, or publisher runtime.

Validation before deployment:

- `python -m compileall src tests tools`: passed.
- `pytest -q tests`: 295 passed.
- Focused publisher/package tests: 41 passed.
- `python tools/build_pdf_dependency_layer.py`: passed after network approval
  for pinned dependency retrieval.
- `python tools/build_lambda_packages.py`: passed.
- `python tools/validate_lambda_artifacts.py`: passed.
- `terraform fmt -recursive -check`: passed.
- `terraform validate`: passed.
- Terraform tests:
  - `tests/observability.tftest.hcl`: 5 passed.
  - `tests/regional_compute.tftest.hcl`: 3 passed.
  - `tests/regional_api_gateway.tftest.hcl`: 4 passed.
  - `tests/resume_analysis_mrsc.tftest.hcl`: 2 passed.
  - `tests/regional_foundation.tftest.hcl`: 1 passed.
- `./tools/validate_platform_v2_foundation.sh`: 32 passed, 0 failed.
- `git diff --check`: passed.

Plan and apply evidence:

- Plan for `fdcc0a4` with
  `enable_outbox_publisher_schedule=true`: 0 added, 11 changed, 0 destroyed.
  Changes were limited to EventBridge schedule enablement and deployment ID
  propagation.
- Apply for `fdcc0a4`: 0 added, 11 changed, 0 destroyed.
- Scheduled observation proved both EventBridge rules were `ENABLED` and both
  publishers received scheduled invocations. The first observation failed
  before application code because Terraform pointed the Lambda to
  `handler.lambda_handler`.
- Commit `3cdb262 fix: correct outbox publisher runtime handler` corrected the
  Lambda handler to `handler.handler`.
- Plan for `3cdb262` with
  `enable_outbox_publisher_schedule=true`: 0 added, 9 changed, 0 destroyed.
  Changes were limited to two publisher handler updates plus deployment ID
  propagation.
- Apply for `3cdb262`: 0 added, 9 changed, 0 destroyed.
- Post-apply no-drift plan with
  `enable_outbox_publisher_schedule=true`: exit code 0, no changes.

Scheduled invocation evidence:

| Region | Rule state during observation | Handler | Deployment ID | Result |
| --- | --- | --- | --- | --- |
| `us-east-1` | `ENABLED`, `rate(1 minute)` | `handler.handler` | `3cdb262` | EventBridge invoked publisher; application logged start; DynamoDB query failed because `gsi1` is absent |
| `us-west-2` | `ENABLED`, `rate(1 minute)` | `handler.handler` | `3cdb262` | EventBridge invoked publisher; application logged start; DynamoDB query failed because `gsi1` is absent |

Blocking table/index finding:

- Repository code writes and queries `gsi1pk`/`gsi1sk` for entity lookup and
  outbox status dispatch.
- `core.outbox_publisher.DynamoDbOutboxRepository.list_dispatchable()` queries
  `IndexName="gsi1"` for `OUTBOX_STATUS#PENDING`,
  `OUTBOX_STATUS#FAILED_RETRYABLE`, and `OUTBOX_STATUS#DISPATCHING`.
- Terraform table definition declares only base attributes `pk` and `sk` and
  no `global_secondary_index`.
- Deployed scheduled invocations failed with the bounded DynamoDB validation
  error that the table does not have the specified index `gsi1`.
- Empty-outbox success counts were not observed because the query failed
  before the publisher could report `examined=0`, `published=0`, and
  `failed=0`.

Safety response:

- No synthetic principal was created.
- No PDF was created or uploaded.
- No target-career, analysis, idempotency, outbox, result, or queue work was
  created.
- No DynamoDB business item was read or written.
- No queue message was manually sent, received, deleted, purged, or redriven.
- No Lambda was manually invoked.
- Both schedules were disabled again through Terraform after the missing-index
  blocker was captured.
- Safety disable plan: 0 added, 2 changed, 0 destroyed.
- Safety disable apply: 0 added, 2 changed, 0 destroyed.
- Final no-drift plan with
  `enable_outbox_publisher_schedule=false`: exit code 0, no changes.

Post-observation state:

| Region | Final schedule state | Queue visible | Queue in flight | Queue delayed | DLQ visible | Health |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `us-east-1` | `DISABLED` | 0 | 0 | 0 | 0 | live 200, ready 200 |
| `us-west-2` | `DISABLED` | 0 | 0 | 0 | 0 | live 200, ready 200 |

Alarm state:

- Outbox publish-failure alarms remained `OK` because no outbox event reached
  publisher delivery logic.
- DLQ alarms remained `OK`.
- Processing queues remained empty.
- Publisher Lambda error alarms entered `ALARM` from the observed missing-index
  failures and were still in `ALARM` at the final check. This is an expected
  consequence of the failed MR-009D3C observation, not a successful validation
  result.

MR-009D3C decision:

MR-009D3C is blocked. It proved the normal EventBridge trigger can reach both
regional publisher Lambdas, and it corrected the publisher handler entrypoint,
but it did not prove successful empty scheduled publisher execution. The next
authorized remediation must align the DynamoDB `gsi1` table/index contract
with repository code before MR-009D3B synthetic runtime validation can restart.

## 30. Documentation Created or Updated

Created:

- `docs/operations/platform-v2/MR-009D_RUNTIME_EVIDENCE_REPORT.md`
- `docs/architecture/decisions/MS-010_OUTBOX_PUBLISHER_SCHEDULE_ACTIVATION.md`

Updated:

- `docs/engineering/MULTI_SITE_COMPLETION_PLAN.md`
- `docs/engineering/CODEX_WORKING_CONTEXT.md`
- `docs/operations/platform-v2/MR-009D_RUNTIME_VALIDATION_PLAN.md`
- `docs/operations/platform-v2/MR-009D_DEPLOYMENT_REPORT.md`
- `docs/runbooks/OUTBOX_OPERATIONS.md`

## 31. Final Repository Validation

Final validation for the implementation commits completed before deployment.
The final documentation-only edit was checked with `git diff --check`.

Completed:

- `python -m compileall src tests tools`: passed.
- `pytest -q tests`: 295 passed.
- `python tools/build_pdf_dependency_layer.py`: passed.
- `python tools/build_lambda_packages.py`: passed.
- `python tools/validate_lambda_artifacts.py`: passed.
- `terraform fmt -recursive -check`: passed.
- `terraform validate`: passed.
- Required Terraform tests listed in the MR-009D3C section: passed.
- `./tools/validate_platform_v2_foundation.sh`: 32 passed, 0 failed.
- `git diff --check`: passed.
- Final Terraform no-drift plan with
  `enable_outbox_publisher_schedule=false`: exit code 0, no changes.

## 32. Commit Created, if Applicable

Two local commits were created for MR-009D3C. A completion commit was not
created because the trigger proof is blocked.

## 33. Commit Hash and Subject

- `fdcc0a4 feat: enable controlled outbox publisher scheduling`
- `3cdb262 fix: correct outbox publisher runtime handler`

## 34. Repository Status

MR-009D documentation is modified locally with this blocked evidence update.
Generated `build/` artifacts remain untracked and must not be committed.

## 35. MR-009D Completion Assessment

MR-009D is not complete. The deployment prerequisite is still healthy, but
synthetic asynchronous runtime behavior was not proven. MR-009D3A corrected
route reachability and placement testability; MR-009D3B then confirmed that
the normal outbox publisher trigger remained disabled. MR-009D3C made the
trigger configurable and proved EventBridge reachability, but successful
publisher execution is blocked by the missing deployed `gsi1` table index.
No synthetic business work was created.

Required missing evidence:

- synthetic business work accepted by both active regional APIs.
- successful empty scheduled outbox publisher invocation through the accepted
  runtime trigger.
- local outbox, queue, worker, and final-state evidence in both regions.
- cross-region owner-region transport and worker evidence.
- runtime idempotency same-payload and conflict behavior.
- end-to-end correlation reconstruction for local and cross-region flows.

## 36. MR-010 Entry Recommendation

Do not start MR-010. Before MR-009D can close, MR-009D3B must use the
corrected route contract and approved development validation override to prove
local and cross-region asynchronous processing, idempotency, correlation,
monitoring, cleanup, and witness boundaries in the deployed development
runtime. A prerequisite remediation is now required to make the outbox
publisher's DynamoDB `gsi1` query contract operational without introducing
replay, retry, failover, traffic shifting, or manual queue delivery behavior.

MR-010 still requires a failover/recovery decision record and failure-mode
review before implementation.

## 37. Runtime Validation Decision

RUNTIME VALIDATION NOT COMPLETE

## MR-009D3D DynamoDB GSI Contract Alignment

MR-009D3D is the prerequisite remediation for the missing deployed `gsi1`
index found during MR-009D3C. No synthetic business work is created in this
slice.

Accepted `gsi1` contract:

- index name: `gsi1`;
- partition key: `gsi1pk`, string;
- sort key: `gsi1sk`, string;
- projection: `ALL`;
- sparse by design.

Usage inventory:

- `core.keys.base_keys()` writes entity lookup keys for domain records that
  require by-entity access.
- `core.storage.get_entity_by_id()` queries `gsi1` for display and fallback
  entity lookup.
- worker fallback lookup queries `gsi1` for legacy queue messages without base
  keys.
- `core.outbox.build_outbox_event()` writes dispatchable outbox records under
  status partitions such as `OUTBOX_STATUS#PENDING`.
- `core.outbox_publisher.DynamoDbOutboxRepository.list_dispatchable()` queries
  `gsi1` for pending, retryable, and stale dispatching records. It does not
  scan the table.
- idempotency and base-key-only profile records intentionally omit the index
  attributes.

Projection decision: `ALL` is required by the current access pattern because
entity lookup returns the indexed item directly and publisher dispatch needs
complete event, ownership, payload, version, request, correlation, lease, and
timestamp fields without a follow-up read.

Hot-partition assessment: outbox status partitions such as
`OUTBOX_STATUS#PENDING` are acceptable for development validation and current
low-volume operation. Before high-volume production schedule activation, this
key shape should be reassessed for sustained publisher throughput.

Implementation validation completed before deployment planning:

- `python -m compileall src tests tools`: passed.
- `pytest -q tests`: 299 passed.
- Focused GSI/outbox/publisher/idempotency tests: 134 passed.
- Lambda package builds and artifact validation: passed.
- Required Terraform tests for observability, regional compute, regional
  foundation, regional API Gateway, and MRSC table contract: passed.
- `./tools/validate_platform_v2_foundation.sh`: 32 passed, 0 failed.
- `git diff --check`: passed.

Phase 1 plan must use `enable_outbox_publisher_schedule=false` and must show an
in-place table update only for the GSI contract, deployment-ID propagation, and
safe outputs. It must not replace or destroy the table, west replica, witness,
queues, DLQs, API Gateway, Cognito, buckets, or other durable resources.

Phase 2 must run only after table status and `gsi1` status are `ACTIVE`, with
the west replica and witness still `ACTIVE`. It then enables the active-region
publisher schedules and observes empty EventBridge-triggered cycles with zero
examined, claimed, published, failed, skipped, and permanently failed records.

MR-009D remains open until MR-009D3D verifies the index and empty publisher
cycles, and MR-009D3B later proves the full synthetic local and cross-region
workflow.

## Required Confirmations

- Only AWS profile `mpopsaws-ai-resume-coach-mike` was used.
- The target remained development.
- No profile, role, workspace, backend, or default region changed.
- Terraform apply occurred only for the reviewed MR-009D3C development plans:
  schedule enablement, publisher handler repair, and safety schedule disable.
- Infrastructure/application deployment occurred only for the reviewed
  MR-009D3C development plans.
- No Terraform import occurred.
- No Terraform state was manually edited.
- No durable data resource was replaced or destroyed.
- No production or staging resource was accessed.
- Only synthetic non-sensitive data was planned.
- No real resume, applicant, employer, job, user, or customer data was used.
- No unrelated DynamoDB item was read.
- No table scan occurred.
- No direct DynamoDB business write occurred.
- No DynamoDB business item was read or written.
- No arbitrary SQS message was received or deleted.
- No SQS message was manually sent.
- No queue was purged.
- No DLQ was redriven.
- No Lambda was manually invoked.
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
- No publisher schedule exists in the witness.
- No secret, password, or token was recorded.
- No temporary token files were created.
- No synthetic Cognito principal was created.
- No synthetic PDF was created or uploaded.
- No synthetic business work was created.
- Generated build artifacts were not committed.
- MR-010 was not started.
- Architecture posters were not regenerated.
- Human engineering ownership remained explicit.
