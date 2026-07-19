# MR-009D Development Deployment Report

## Status

Development deployment prerequisite verified on 2026-07-18T16:58Z.

Terraform deployment succeeded after adopting one existing legacy log group:

- Resources added: 120.
- Resources changed: 1.
- Resources destroyed: 0.

Two narrow repair deployments then completed:

- PDF dependency repair: 2 resources added, 10 changed, 0 destroyed.
- API readiness IAM repair: 0 resources added, 11 changed, 0 destroyed.

The deployed active-region APIs now initialize successfully. Both
`/health/live` and `/health/ready` pass in `us-east-1` and `us-west-2` with
deployment ID `3fe0077`.

MR-009D deployment prerequisite is verified. Synthetic end-to-end runtime
validation remains pending and must be performed as MR-009D3 with separate
authorization.

MR-009D3B found one remaining runtime-validation prerequisite blocker:
regional outbox-publisher schedules existed but were disabled. MR-009D3C is
the authorized remediation to make those schedules explicitly configurable,
keep them disabled by default, and enable them for the development validation
deployment only.

MR-009D3C deployed schedule control and the publisher handler correction at
deployment ID `3cdb262`. EventBridge invoked both active-region publishers,
but the empty scheduled invocations failed because the deployed DynamoDB table
does not include the `gsi1` index used by the repository outbox status query.
Both schedules were disabled again through Terraform after the failure was
captured. MR-009D runtime validation remains blocked until the table/index
contract is remediated.

MR-009D3D remediated this prerequisite at deployment ID `2b87e4d` by adding the
repository-required sparse `gsi1` index (`gsi1pk`/`gsi1sk`, projection `ALL`)
in place. The deployment was performed in two phases: add the index with
publisher schedules disabled, wait for `gsi1` to become `ACTIVE`, then enable
development schedules and verify empty publisher cycles without creating
synthetic business records.

## Scope

Original milestone commit targeted:

```text
9c9c28e feat: complete active-active routing, transport, traceability, and health foundation
```

Repair commits deployed:

```text
35c722f fix: attach PDF dependency layer to regional APIs
3fe0077 fix: permit API readiness dependency checks
```

Current selected deployment ID:

```text
3fe0077
```

Target:

- Environment: `dev`.
- Active regions: `us-east-1`, `us-west-2`.
- Witness region: `us-east-2`.
- AWS profile: `mpopsaws-ai-resume-coach-mike`.
- Account: `[redacted-account]`.
- Terraform backend: S3 backend with development key
  `ai-resume-coach/dev/terraform.tfstate`.
- Terraform workspace: `default`.

## Repository and Git State

The deployable source matched the accepted milestone commit before import,
planning, and apply. Dirty worktree files were limited to MR-009D
documentation.

Two local repair commits were created. No Git push was performed.

## Import Decision

The existing log group
`/aws/lambda/ai-resume-coach-dev-registration-notification` was safe to adopt:

- exact name matched Terraform resource `aws_cloudwatch_log_group.registration_notification`;
- no corresponding Lambda existed before deployment;
- no subscription filters or metric filters were configured;
- no data-protection policy or KMS key was configured;
- no other Terraform state was known to manage it;
- no production-use evidence was found.

Import command used sanitized non-secret deployment inputs and imported only
that one log group. Post-import state contained exactly one managed resource
instance plus Terraform data-source entries.

Expected post-import diff was an in-place retention and tag update. The
reviewed plan showed the imported log group changing from no retention to
14-day retention and receiving Terraform tags.

## Explicit Deployment Inputs

All Terraform plan/apply commands were run with ambient deployment variables
neutralized for command scope:

- `TF_VAR_openai_api_key` unset;
- `TF_VAR_analysis_provider` unset;
- `TF_VAR_deployment_id` unset.

Initial infrastructure deployment values supplied:

- `environment=dev`;
- `deployment_id=9c9c28e`;
- `analysis_provider=rule-based`;
- `openai_api_key=` empty;
- `enable_operational_alarms=true`;
- `enable_observability_dashboard=true`.

No secret value was recorded. No `.tfvars` file containing secrets was created.

Repair deployment values used the same command-scoped sanitization with
deployment IDs `35c722f` and then `3fe0077`.

## Validation Before Apply

Passed before planning/apply:

- `python -m compileall src tests`.
- Focused runtime-adjacent Python tests: 223 passed.
- Full Python suite: 271 passed.
- `terraform fmt -recursive -check`.
- `terraform validate`.
- `terraform test -filter=tests/observability.tftest.hcl`: 5 passed, 0 failed.
- `terraform test -filter=tests/regional_compute.tftest.hcl`: 1 passed, 0 failed.
- `terraform test -filter=tests/regional_api_gateway.tftest.hcl`: 2 passed, 0 failed.
- `terraform test -filter=tests/resume_analysis_mrsc.tftest.hcl`: 2 passed, 0 failed.
- `./tools/validate_platform_v2_foundation.sh`: 28 passed, 0 failed.
- `git diff --check`.

Additional D2B validation before repair deployments:

- `python -m compileall src tests tools`.
- Full Python suite: 274 passed.
- `python tools/build_pdf_dependency_layer.py`.
- `python tools/build_lambda_packages.py`.
- `python tools/validate_lambda_artifacts.py`.
- `terraform fmt -recursive -check`.
- `terraform validate`.
- `terraform test -filter=tests/observability.tftest.hcl`: 5 passed, 0 failed.
- `terraform test -filter=tests/regional_compute.tftest.hcl`: 1 passed, 0 failed.
- `terraform test -filter=tests/regional_api_gateway.tftest.hcl`: 2 passed, 0 failed.
- `terraform test -filter=tests/resume_analysis_mrsc.tftest.hcl`: 2 passed, 0 failed.
- `./tools/validate_platform_v2_foundation.sh`: 28 passed, 0 failed.
- `git diff --check`.

## Reviewed Terraform Plan

Sanitized saved plan:

- Managed resource changes: 121.
- Creates: 120.
- Updates in place: 1.
- Replacements: 0.
- Destroys: 0.

Resource types planned:

- API Gateway HTTP APIs, stages, authorizers, integrations, and routes.
- Regional API, worker, and outbox-publisher Lambdas.
- Registration-notification Lambda.
- DynamoDB Resume Analysis table with west active replica and east witness.
- Regional SQS processing queues and DLQs.
- Regional Lambda event-source mappings.
- IAM roles, inline policies, permissions, and policy attachments.
- Regional CloudWatch log groups.
- Regional EventBridge outbox publisher schedules.
- One operations dashboard.
- 22 CloudWatch alarms, 11 per active region.
- Regional document buckets and bucket controls.
- Registration SNS topic.
- Cognito user pool, client, and domain.

Pre-apply collision checks found no remaining unmanaged collisions for the
planned current regional API names, queue names, document bucket names,
DynamoDB table name, registration IAM role name, Cognito domain, or current
regional log-group names.

## Apply Result

The exact reviewed saved plan was applied.

- Resources added: 120.
- Resources changed: 1.
- Resources destroyed: 0.

No manual AWS changes accompanied the apply.

Immediate Terraform verification:

- state is populated with 127 listed entries, including data sources;
- sanitized outputs are populated;
- east and west deployment IDs are both `9c9c28e`;
- observability alarms are enabled;
- dashboard is enabled;
- `terraform plan -detailed-exitcode` with the same sanitized inputs returned
  no changes.

The temporary saved plan file was removed from `/tmp` after verification.

## D2B Repair Summary

Root cause:

```text
handler
  -> route registration / feature import
  -> features.resume_analysis
  -> pypdf
```

The API package imports `features.resume_analysis` during Lambda
initialization. That module imports `pypdf` at module scope, so health
requests could not reach dependency-free liveness until the runtime artifact
provided the dependency.

Selected packaging model:

- shared Terraform-managed PDF dependency layer;
- one layer version in `us-east-1`;
- one equivalent layer version in `us-west-2`;
- identical layer content and source hash;
- attached only to the regional API Lambdas;
- no layer in the witness region;
- no layer attached to workers, outbox publishers, or registration
  notification.

The layer is built from `lambda_layer/requirements.txt` by
`tools/build_pdf_dependency_layer.py` for Python 3.13 arm64 Lambda
compatibility and includes `python/pypdf/`.

Additional artifact validation now proves:

- API handler import succeeds with only packaged API code and the layer path;
- API handler import fails without the PDF dependency layer;
- worker, outbox publisher, and registration notification packages initialize
  without the PDF layer;
- generated artifacts do not include `.env`, Terraform state, caches, or
  credential paths.

Readiness then reached handler code but failed because the API role lacked
the read-only readiness actions it performs. The API runtime policy now
includes:

- `dynamodb:DescribeTable`;
- `sqs:GetQueueAttributes`.

No CloudWatch read permissions, alarm permissions, routing permissions, or
control-plane authority were added.

The operations dashboard was updated with one east/west comparative
`Processing DLQ Depth` widget using `AWS/SQS`
`ApproximateNumberOfMessagesVisible`.

D2B Terraform applies:

- PDF dependency layer deployment: 2 added, 10 changed, 0 destroyed.
- API readiness IAM deployment: 0 added, 11 changed, 0 destroyed.
- Post-apply drift check with deployment ID `3fe0077`: no changes.
- Temporary saved plan file removed from `/tmp`.

## Regional Inventory

### East: `us-east-1`

Verified present:

- regional API Lambda;
- worker Lambda;
- outbox-publisher Lambda;
- registration-notification Lambda;
- regional HTTP API Gateway;
- processing queue;
- processing DLQ;
- worker event-source mapping;
- document bucket;
- CloudWatch log groups;
- 11 regional alarms.

Runtime configuration summary:

- API Lambda: Python 3.13, arm64, 512 MB, 30 second timeout, deployment ID
  `3fe0077`, site `east`, role `active`, environment `dev`, one local PDF
  dependency layer.
- Worker Lambda: Python 3.13, arm64, 1024 MB, 120 second timeout, deployment
  ID `3fe0077`, site `east`, role `active`, environment `dev`, no PDF layer.
- Outbox publisher Lambda: Python 3.13, arm64, 256 MB, 30 second timeout,
  deployment ID `3fe0077`, site `east`, role `active`, environment `dev`, no
  PDF layer.

### West: `us-west-2`

Verified present:

- regional API Lambda;
- worker Lambda;
- outbox-publisher Lambda;
- regional HTTP API Gateway;
- processing queue;
- processing DLQ;
- worker event-source mapping;
- document bucket;
- CloudWatch log groups;
- 11 regional alarms.

Runtime configuration summary:

- API Lambda: Python 3.13, arm64, 512 MB, 30 second timeout, deployment ID
  `3fe0077`, site `west`, role `active`, environment `dev`, one local PDF
  dependency layer.
- Worker Lambda: Python 3.13, arm64, 1024 MB, 120 second timeout, deployment
  ID `3fe0077`, site `west`, role `active`, environment `dev`, no PDF layer.
- Outbox publisher Lambda: Python 3.13, arm64, 256 MB, 30 second timeout,
  deployment ID `3fe0077`, site `west`, role `active`, environment `dev`, no
  PDF layer.

### Witness: `us-east-2`

Verified:

- DynamoDB witness status is active.
- No application Lambda functions with the project development prefix.
- No application processing queues with the project development prefix.
- No application API Gateway APIs with the project development prefix.
- No active-region CloudWatch alarms with the project development prefix.

Witness responsibilities remain limited to the accepted data witness role.

## DynamoDB Topology

Verified without reading table items:

- Table status: `ACTIVE`.
- Billing mode: `PAY_PER_REQUEST`.
- Key schema: `pk` hash key and `sk` range key.
- Active replica: `us-west-2`, status `ACTIVE`.
- Witness: `us-east-2`, status `ACTIVE`.
- Server-side encryption: enabled.
- Point-in-time recovery: enabled.
- Deletion protection: disabled for development.

No DynamoDB business item was scanned, queried, read, written, updated, or
deleted.

## Queue and Worker Wiring

Verified for both active regions:

- processing queue exists;
- processing DLQ exists;
- SQS-managed encryption is enabled;
- processing queue visibility timeout is 180 seconds;
- worker timeout is 120 seconds;
- redrive policy sends to the regional DLQ after 5 receives;
- worker event-source mapping is enabled;
- batch size is 5;
- partial batch failure reporting uses `ReportBatchItemFailures`;
- approximate queue and DLQ visible-message counts were 0 at verification time.

No SQS message was sent, received, deleted, purged, or redriven.

## Health Endpoint Results

Read-only diagnostic endpoint invocations were performed after the D2B repair
deployments.

Results:

- east `/health/live`: HTTP 200, approximately 1.32 seconds.
- east `/health/ready`: HTTP 200, approximately 1.34 seconds.
- west `/health/live`: HTTP 200, approximately 1.20 seconds.
- west `/health/ready`: HTTP 200, approximately 1.72 seconds.

Liveness evidence:

- east reports `region=us-east-1`, `siteName=east`, `regionRole=active`,
  `environment=dev`, `deploymentId=3fe0077`;
- west reports `region=us-west-2`, `siteName=west`, `regionRole=active`,
  `environment=dev`, `deploymentId=3fe0077`.

Readiness evidence:

- `regionalHealth.scope` is `readiness`;
- both regions return `status=ready`;
- both regions return readiness classification `HEALTHY`;
- bounded reason code is `ALL_REQUIRED_CHECKS_PASS`;
- observations are current and fresh;
- configuration, DynamoDB, and SQS checks pass in both regions.

Recent API Lambda logs in both active regions show handler initialization and
health requests reaching application code. No new
`Runtime.ImportModuleError` or `No module named 'pypdf'` events appeared after
the D2B repair deployment.

Health responses remained sanitized: no raw exceptions, account IDs, ARNs,
table names, queue URLs, credentials, or user payloads were returned.

## Monitoring Results

Verified:

- 11 alarms exist in `us-east-1`.
- 11 alarms exist in `us-west-2`.
- All expected alarms were in `OK` state at verification time.
- All expected alarms use `treat_missing_data=notBreaching`.
- Alarm actions are empty; no alarm action changes runtime behavior.
- One operations dashboard exists.

Alarm categories present per active region:

- API 5xx;
- API latency;
- API Lambda errors;
- worker Lambda errors;
- outbox-publisher Lambda errors;
- processing queue depth;
- processing queue oldest-message age;
- processing DLQ messages;
- DynamoDB throttling;
- worker-record failures;
- outbox-publish failures.

Dashboard coverage verified:

- API request/error comparison;
- API latency;
- Lambda errors;
- Lambda throttles;
- processing queue depth and oldest-message age;
- worker-record failures;
- outbox-publish failures;
- processing DLQ depth;
- DynamoDB throttling;
- east/west comparison.

## Legacy Resource Disposition

- Registration-notification log group: now managed by Terraform.
- Legacy non-regional API log group: retained, superseded, cleanup candidate.
- Legacy non-regional worker log group: retained, superseded, cleanup
  candidate.
- Legacy IAM role `ai-resume-coach-dev-lambda-execution-role`: retained,
  superseded, cleanup candidate.
- Stale or non-describable Cognito tag mapping: retained, requires separate
  cleanup/ownership decision.
- Terraform lock table: retained as backend support infrastructure.

No legacy resource was deleted.

## Discrepancies and Blockers

Resolved during D2B:

- API package/runtime dependency mismatch: repaired by regional API PDF
  dependency layers and artifact validation.
- API readiness IAM mismatch: repaired by adding the two read-only dependency
  check actions required by `/health/ready`.
- Operations dashboard lacked a dedicated DLQ-depth widget: repaired with one
  bounded east/west comparative widget.

Remaining blockers for MR-009D deployment prerequisite:

- none known.

Deferred validation:

- synthetic business-work creation;
- local transport processing;
- cross-region transport processing;
- worker execution evidence;
- end-to-end correlation reconstruction;
- idempotency runtime behavior.

MR-009D3 follow-up found that the deployment prerequisite remains healthy, but
synthetic end-to-end validation is blocked before business work creation. The
deployed API Gateway protected route set does not expose the application
handler's supported asynchronous upload-analysis routes
`POST /resume-upload-url` and `POST /analyze-uploaded-resume`. The attempted
runtime evidence is recorded in
`docs/operations/platform-v2/MR-009D_RUNTIME_EVIDENCE_REPORT.md`, and MR-009D
remains open.

MR-009D3A is authorized to remediate the route-contract drift and add
development-only remote-owner placement testability. The planned deployment
changes are limited to regional API Gateway route additions/removals, Lambda
package/config updates, the dedicated validation Cognito group when explicitly
enabled for development, and documentation/tests. It must not create synthetic
business work; MR-009D3B remains the runtime evidence slice.

## Next Authorization Required

The next task should be MR-009D3 synthetic end-to-end runtime validation. It
requires explicit authorization before creating any synthetic business work,
invoking write endpoints, inspecting application records, or validating local
and cross-region transport behavior.

## Required Confirmations

- Only AWS profile `mpopsaws-ai-resume-coach-mike` was used.
- The target remained development.
- No account, profile, role, workspace, backend, or default region was changed.
- No backend migration occurred.
- Only the explicitly authorized log group was imported.
- No other Terraform import occurred.
- No Terraform state was manually edited, moved, or removed.
- No Terraform destroy occurred.
- No legacy resource was deleted.
- No Git push occurred.
- No production or staging deployment occurred.
- Ambient secret-bearing Terraform variables were not used by the final plan.
- No secret-bearing plan file was retained.
- No synthetic business work was created.
- No business API write endpoint was invoked.
- No DynamoDB business item was read or written.
- No SQS message was sent, received, deleted, purged, or redriven.
- No ownership or outbox record was manually changed.
- No failover occurred.
- No traffic shifting occurred.
- No DNS or global-routing behavior was changed beyond accepted development
  infrastructure deployment.
- No replay occurred.
- No transport retry was introduced.
- No queue draining occurred.
- No automatic recovery was introduced.
- Health remained diagnostic and readiness-scoped.
- Witness responsibilities remained unchanged.
- MR-010 was not started.
- Architecture posters were not regenerated.
- Human engineering ownership remained explicit.
