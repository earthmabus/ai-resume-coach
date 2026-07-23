# Multi-Site Operations Runbook

## Scope

This is the authoritative operator procedure for Platform V2 multi-site health checks, routing isolation, worker interruption recovery, certification, and emergency restoration.

## Safety invariants

- Never disable both site routing records.
- Never mutate `ownerRegion` to recover work.
- Never move queue messages across regions manually.
- Never use infrastructure rollback to reverse application data.
- Do not expose tokens, presigned URLs, resume content, prompts, or provider payloads in committed evidence.
- Treat direct reachability of a routing-isolated site as expected.

## Normal health check

Run the non-mutating gate:

```bash
./tools/validate/operational_readiness.sh
```

A healthy result verifies both regional readiness endpoints, publishers, APIs, workers, queues, DLQs, event-source mappings, the DynamoDB table, active replicas, and the MRSC witness contract.

For direct inspection, call each regional `/health/live` and `/health/ready` endpoint. `/health/live` proves process execution only. `/health/ready` supplies bounded dependency readiness and runtime identity.

## Routing isolation

Use the reviewed MR-009D4 harness rather than ad hoc Terraform commands:

```bash
export TFVARS_FILE="$PWD/infra/.terraform-build/mr014-certification.tfvars"
export AUTH_TOKEN='<fresh Cognito ID token>'
export EXECUTE_FAILOVER=YES
export CONFIRM_MUTATION=YES

./tools/validate/failover_runtime.sh
```

Expected behavior:

1. runtime inputs align to deployed Lambda configuration;
2. the routing-only plan changes only the intended Route 53 record and outputs;
3. the global API converges to the survivor;
4. authenticated synthetic work succeeds;
5. new work is owned by the survivor;
6. reads succeed;
7. both routing records are restored.

## Worker interruption recovery

The MR-014 worker scenario is the accepted procedure:

```bash
export TFVARS_FILE="$PWD/infra/.terraform-build/mr014-certification.tfvars"
export AUTH_TOKEN='<fresh Cognito ID token>'
export EXECUTE_CHAOS=YES
export CONFIRM_MUTATION=YES

./tools/validate/chaos.sh worker-certification
```

The procedure disables one event-source mapping, submits duplicate-idempotent work, waits for visible or in-flight backlog, restores the mapping, confirms state `Enabled`, waits for one workflow to complete, and verifies queue drain.

Do not declare recovery from the enable API response alone.

## Full certification

```bash
source ./tools/prepare/auth.sh
export TFVARS_FILE="$PWD/infra/.terraform-build/mr014-certification.tfvars"

set -o pipefail
CONFIRM_MUTATION=YES \
EXECUTE_CHAOS=YES \
./tools/validate/chaos.sh certify \
2>&1 | tee "evidence/mr014-chaos-$(date +%Y%m%dT%H%M%S).log"

status=$?
echo "MR-014 exit status: $status"
```

Certification requires exit status `0`, final `report.json` result `PASS`, `complete: true`, four scenarios executed, and four scenarios passed.

## Evidence review

```bash
run="$(ls -1dt evidence/mr014-certify-* | head -1)"

find "$run/steps" -name results.json -print -exec cat {} \;
cat "$run/report.json"
```

Worker evidence should include at least:

- `disable.json`
- `backlog-latest.json`
- `enable.json`
- `analysis-latest.json`
- `queue-drain-latest.json`
- `results.json`
- `execution.log`

## Emergency routing restoration

If a routing exercise is interrupted, first inspect the harness exit-trap evidence. If either record remains disabled, restore both explicitly:

```bash
terraform -chdir=infra plan \
  -var-file="$TFVARS_FILE" \
  -var='site_routing_enabled={east=true,west=true}' \
  -out=restore-routing.tfplan

terraform -chdir=infra apply restore-routing.tfplan
```

Then verify both direct readiness endpoints, global API health, Terraform outputs, and Route 53 records.

## Emergency worker restoration

Use the mapping UUID from Terraform output or the scenario catalog:

```bash
aws lambda update-event-source-mapping \
  --region <worker-region> \
  --uuid <mapping-uuid> \
  --enabled

aws lambda get-event-source-mapping \
  --region <worker-region> \
  --uuid <mapping-uuid>
```

Wait until `State` is `Enabled`. Then inspect queue visible and not-visible counts, worker errors, DLQs, and the affected workflow state.

## Incident evidence

Capture caller identity, Terraform outputs, direct and global health, Route 53 state, Lambda mappings, queue attributes, DLQ attributes, DynamoDB table status, relevant structured logs, deployment ID, timestamps, commands, and restoration actions.

Commit only a sanitized summary. Preserve raw environment evidence according to the local evidence-retention policy.

## Escalation boundaries

Manual intervention is required for terminal failures, poison messages, or data-level repair. The current platform does not automatically replay terminal failures, reassign owners, drain a queue into another region, or provide an operator recovery console.
