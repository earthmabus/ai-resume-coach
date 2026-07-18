# MR-009D Read-Only Runtime Discovery Report

## Status

Read-only discovery completed with limitations on 2026-07-18T15:12:05Z.

This report does not mark MR-009D runtime validation complete. No deployed
runtime write path was exercised, and no synthetic work item was created.

Follow-up note: MR-009D2A later deployed the development infrastructure after
adopting one legacy log group. The "not found" runtime inventory below remains
the result of this read-only discovery at the time it was performed, but it no
longer represents current deployed state. Current deployment evidence is
recorded in `docs/operations/platform-v2/MR-009D_DEPLOYMENT_REPORT.md`.

## Scope

Commit inspected:

```text
9c9c28e feat: complete active-active routing, transport, traceability, and health foundation
```

AWS profile used:

```text
mpopsaws-ai-resume-coach-mike
```

Authorization scope:

- read-only discovery of the AI Resume Coach development environment;
- read-only AWS identity, configuration, resource, metric, alarm, dashboard,
  log-metadata, and health-endpoint discovery;
- no deployment, Terraform apply, data mutation, queue mutation, routing
  change, or synthetic business-data creation.

## AWS Identity

The selected profile resolved successfully through STS.

- Principal type: IAM user.
- Caller ARN: `arn:aws:iam::[redacted-account]:user/mike`.
- Account alias: none configured.
- Default profile region: `us-east-1`.
- Credential validity: valid at discovery time.
- Session expiration: not visible from STS output for this IAM user.
- MFA or role chaining: not indicated by the caller ARN.

The account is strongly indicated to be the repository's AI Resume Coach AWS
account because the redacted account identifier matches the account suffix
embedded in the repository Terraform backend bucket name. The report does not
record the account number.

## Terraform Backend and Workspace

Repository backend:

- Backend type: S3.
- Backend bucket: `earthmabus-ai-resume-coach-tfstate-[redacted-account]`.
- Backend key: `ai-resume-coach/dev/terraform.tfstate`.
- Backend region: `us-east-1`.
- Lock mechanism: S3 native lockfile.

Local Terraform state configuration:

- Current workspace: `default`.
- `.terraform/environment`: absent.
- Local `.terraform/terraform.tfstate`: backend metadata only.
- `terraform output -json`: `{}`.
- `terraform state list`: no resources returned.

Assessment: the configured backend/workspace is development-oriented by key,
but it currently exposes no managed platform resources or outputs. Runtime
discovery therefore could not rely on Terraform outputs.

## Environment Assessment

Environment confidence: strongly indicated development, not fully verified.

Evidence:

- Terraform backend key contains `dev`.
- Repository default `terraform.tfvars.example` uses `environment = "dev"`.
- One tagged Cognito user-pool resource in `us-east-1` carries
  `Project=ai-resume-coach`, `ManagedBy=Terraform`, and `Environment=dev`.
- No Terraform state resources or outputs were available from the selected
  backend/workspace.

Expected active regions:

- East: `us-east-1`.
- West: `us-west-2`.

Expected witness region:

- `us-east-2`.

Expected deployment ID:

- Unable to determine from deployed runtime; no application Lambda or API
  runtime was found.

## Regional Component Inventory

Discovery used repository-derived names and tags, including
`Project=ai-resume-coach` and `ai-resume-coach-dev` naming conventions. It did
not enumerate unrelated account resources.

### us-east-1

Found:

- One tagged Cognito user pool for the development environment.
- One DynamoDB table named for Terraform locking.
- Legacy Lambda log groups for earlier non-regional function names:
  `ai-resume-coach-dev-api`, `ai-resume-coach-dev-registration-notification`,
  and `ai-resume-coach-dev-resume-analysis-worker`.

Not found:

- Regional API Lambda.
- Regional worker Lambda.
- Regional outbox-publisher Lambda.
- Regional HTTP API Gateway API.
- Regional `processing_queue`.
- Regional `processing_dlq`.
- Regional CloudWatch alarms with the expected project prefix.
- Platform operations dashboard with the expected project prefix.
- Application DynamoDB table.
- CloudFormation stacks with the expected project name.

### us-west-2

Found:

- No tagged AI Resume Coach resources.

Not found:

- Regional API Lambda.
- Regional worker Lambda.
- Regional outbox-publisher Lambda.
- Regional HTTP API Gateway API.
- Regional `processing_queue`.
- Regional `processing_dlq`.
- Regional CloudWatch alarms with the expected project prefix.
- Application DynamoDB table.
- Lambda log groups with the expected project prefix.
- CloudFormation stacks with the expected project name.

### us-east-2

Found:

- No tagged AI Resume Coach resources.

Not found:

- Application Lambdas.
- Regional HTTP API Gateway API.
- Regional processing queues.
- Application monitoring stack.
- DynamoDB application witness resources.
- CloudFormation stacks with the expected project name.

Witness assessment: the witness does not host application runtime resources,
which is consistent with the accepted witness role, but the expected MRSC
witness data resource was not observed.

## Deployed-Version Assessment

No application Lambda functions matching the repository naming conventions were
found in `us-east-1`, `us-west-2`, or `us-east-2`.

Component classification:

- East API Lambda: unable to determine; not found.
- East worker Lambda: unable to determine; not found.
- East outbox publisher Lambda: unable to determine; not found.
- West API Lambda: unable to determine; not found.
- West worker Lambda: unable to determine; not found.
- West outbox publisher Lambda: unable to determine; not found.

No runtime `DEPLOYMENT_ID`, Lambda code SHA-256, runtime version, timeout,
memory, or MR-009B/MR-009C environment configuration could be collected.

## Regional API Discovery

Terraform outputs did not provide regional endpoints. API Gateway v2 discovery
by the repository project name found no regional APIs in `us-east-1`,
`us-west-2`, or `us-east-2`.

Health endpoint invocation was not attempted because no direct regional API
endpoint was discovered.

## Health Endpoint Results

No `/health/live` or `/health/ready` runtime result was collected.

Reason: no direct regional API endpoint was available from Terraform outputs
or read-only API Gateway discovery.

## DynamoDB and Witness Assessment

DynamoDB table listing showed:

- `us-east-1`: Terraform lock table only.
- `us-west-2`: no DynamoDB tables.
- `us-east-2`: no DynamoDB tables.

The application MRSC Resume Analysis table and witness capability were not
observed in the selected backend/workspace/account view. No DynamoDB business
items were scanned or read.

Topology classification: does not currently match the accepted deployed
multi-site application architecture in the selected environment.

## Queue and Event-Source Assessment

SQS discovery by the repository queue-name prefix found no processing queues
or DLQs in `us-east-1`, `us-west-2`, or `us-east-2`.

Lambda event-source mappings could not be evaluated because the expected
worker Lambdas were not found. No SQS messages were received, sent, deleted,
purged, or redriven.

## Observability Assessment

CloudWatch alarm discovery by the repository alarm-name prefix found no
expected active-region alarms in `us-east-1`, `us-west-2`, or `us-east-2`.

Dashboard discovery by the repository dashboard-name prefix found no platform
operations dashboard.

Expected MR-009C alarms were therefore not present in the selected
backend/workspace/account view:

- API 5xx.
- API latency.
- API Lambda errors.
- Worker Lambda errors.
- Outbox-publisher Lambda errors.
- Processing queue depth.
- Processing queue oldest-message age.
- DLQ depth.
- DynamoDB throttling.
- Worker-record failures.
- Outbox-publish failures.

No alarm or dashboard was modified.

## Safe Log Assessment

Safe log-event inspection was not performed because the expected current
regional application Lambda and API log groups were not discovered. Legacy
`us-east-1` Lambda log groups were observed for earlier non-regional function
names, but they were not treated as evidence for the MR-009 active-active
runtime. No raw user logs, resume content, job descriptions, tokens,
credentials, account IDs, raw ARNs, or resource URLs were recorded.

## Deployment Classification

Classification: older deployment / not currently deployed for the MR-009
active-active runtime.

Evidence:

- The selected Terraform backend/workspace returned no state resources and no
  outputs.
- No expected active-region application Lambdas were found.
- No expected regional APIs were found.
- No expected processing queues or DLQs were found.
- No application MRSC DynamoDB table or witness resource was found.
- No expected regional alarms or operations dashboard were found.
- Only pre-runtime/shared development account resources and legacy log groups
  were observed.

MR-009D synthetic runtime validation cannot proceed against this environment
until the active-active runtime is deployed or the correct Terraform
backend/workspace/environment is identified.

## Evidence Limitations

- Account alias is absent, so account purpose is inferred from repository
  backend naming and resource tags rather than a formal alias.
- Terraform state may be empty because the selected workspace/backend has not
  deployed the platform or because a different backend/workspace is
  authoritative for the deployed environment.
- Resource discovery was intentionally scoped to repository-derived names and
  tags and did not enumerate unrelated account resources.
- No health endpoints were invoked because no regional endpoints were found.
- No runtime logs were queried because expected runtime log groups were not
  found.
- No application data, outbox state, queue contents, or DynamoDB items were
  inspected.

## Recommended Next Authorization

Recommended next action: authorize deployment of commit `9c9c28e` through the
approved development deployment workflow, or provide the correct existing
Terraform backend/workspace/environment if the runtime is already deployed
elsewhere.

Required authorization before the next MR-009D execution:

- confirm target account using a non-sensitive account alias or approved
  identifier;
- confirm target environment;
- confirm Terraform backend and workspace;
- confirm expected deployment ID;
- authorize deployment if the selected environment is intentionally empty;
- authorize regional health endpoint invocation after deployment;
- authorize creation of synthetic non-sensitive smoke-test work only after
  deployment is verified;
- define cleanup requirements for synthetic validation records.

## Explicit Confirmations

- Only the already-selected AWS profile was used.
- No account, profile, role, workspace, backend, or region default was changed.
- No Terraform apply was run.
- No Terraform state was modified.
- No application deployment occurred.
- No infrastructure deployment occurred.
- No Git push occurred.
- No business API write operation occurred.
- No synthetic work item was created.
- No DynamoDB item was read, written, updated, or deleted.
- No SQS message was received, sent, deleted, purged, or redriven.
- No Lambda configuration was changed.
- No alarm or dashboard was changed.
- No routing behavior was changed.
- No ownership behavior was changed.
- No outbox state was changed.
- No failover occurred.
- No traffic shifting occurred.
- No replay occurred.
- No retry capability was introduced.
- No queue draining occurred.
- No secret or credential was recorded.
- No personal or resume data was exposed.
- MR-009D was not marked complete.
- MR-010 was not started.
- Architecture posters were not regenerated.
- Human engineering ownership remained explicit.
