# MR-009D4 Regional Isolation and Recovery Runtime Validation Plan

## Objective

Demonstrate that either active site can be removed from global Route 53 routing while the peer site continues serving authenticated application traffic, accepting new resume-analysis work, and reading the resulting MRSC-backed data. Demonstrate restoration after each isolation without data repair.

## Scope

MR-009D4 tests **controlled routing isolation** by removing one latency-routing record at a time through Terraform. It does not stop Lambda, API Gateway, DynamoDB, SQS, or other regional resources. The isolated direct regional endpoint is intentionally expected to remain available for diagnosis and recovery verification.

## Safety invariants

- Never disable both routing records.
- Require `EXECUTE_FAILOVER=YES` and `CONFIRM_MUTATION=YES` before applying changes.
- Use an explicit, operator-supplied `TFVARS_FILE`.
- Install an exit trap that restores `{east=true,west=true}` after interruption or failure.
- Do not modify application ownership, outbox records, queues, or DynamoDB data to simulate recovery.
- Require an ID token with at least 30 minutes of remaining lifetime by default.

## Scenarios

### East isolated

1. Capture direct regional and global baseline evidence.
2. Apply `site_routing_enabled={east=false,west=true}`.
3. Poll the global `/health/ready` endpoint until it reports `us-west-2`.
4. Submit a new authenticated resume analysis through the global hostname.
5. Verify `ownerRegion=us-west-2` through both the global hostname and West direct API.
6. Confirm the East direct health endpoint remains available for diagnosis.
7. Restore both routing records.

### West isolated

Repeat the same flow with `site_routing_enabled={east=true,west=false}`, expecting `ownerRegion=us-east-1`.

## Evidence

The harness stores:

- repository validation output;
- Terraform outputs and AWS caller identity;
- JWT-safe summary and remaining lifetime;
- Terraform plans and applies for every isolation/restoration;
- DNS resolution snapshots;
- global routing convergence polling records;
- direct and global health responses;
- authenticated upload, submission, and read responses;
- ownership assertions;
- safety-restoration output if the run exits unexpectedly;
- a final Markdown report and timestamped execution log.

## Execution

```bash
export AWS_PROFILE=<profile>
export TFVARS_FILE="$PWD/infra/<deployment>.tfvars"
export AUTH_TOKEN='<fresh Cognito ID token>'
export SYNTHETIC_PDF="$PWD/<synthetic-file>.pdf"
export EXECUTE_FAILOVER=YES
export CONFIRM_MUTATION=YES

./tools/validate/failover_runtime.sh
```

Optional controls:

```bash
export MIN_TOKEN_LIFETIME_SECONDS=1800
export ROUTING_CONVERGENCE_TIMEOUT_SECONDS=300
export ROUTING_POLL_INTERVAL_SECONDS=10
export SKIP_REPOSITORY_VALIDATION=YES
```

Use `SKIP_REPOSITORY_VALIDATION=YES` only when the same commit has already passed the complete Python and Terraform suites immediately before execution.

## Acceptance criteria

- East isolation converges global traffic to West within the configured timeout.
- New global work during East isolation is owned and readable through West.
- East routing is restored successfully.
- West isolation converges global traffic to East within the configured timeout.
- New global work during West isolation is owned and readable through East.
- West routing is restored successfully.
- Both direct health endpoints and an authenticated global request succeed after restoration.
- Harness exits `0` and reports `MR-009D4 PASSED`.
