# Regional Isolation and Recovery Runbook

## Isolation model

Routing isolation removes one regional Route 53 latency record. It does not shut down the regional application stack. The isolated direct API remains intentionally reachable for diagnosis, repair, and readiness verification.

## Preconditions

1. Confirm both direct regional `/health/live` and `/health/ready` endpoints succeed.
2. Confirm the global API hostname succeeds.
3. Confirm the peer site can accept authenticated application traffic.
4. Use a fresh Cognito ID token with enough lifetime for isolation and restoration.
5. Identify the exact deployment tfvars file.
6. Preserve pre-change Terraform outputs, caller identity, health, and DNS evidence.

## Isolate one site

1. Set only the affected site's `site_routing_enabled` value to `false`.
2. Review the Terraform plan and confirm it changes only the intended routing record and related outputs.
3. Apply the plan.
4. Poll the global `/health/ready` endpoint until its `region` identifies the surviving site.
5. Submit authenticated synthetic work through the global hostname.
6. Verify the new record's `ownerRegion` through the global hostname and the surviving direct API.
7. Capture both direct regional health endpoints. The isolated direct endpoint should remain available.

## Restore one site

1. Verify the isolated direct endpoint is live and ready.
2. Verify queues, DLQs, event-source mappings, alarms, and MRSC are healthy.
3. Set `site_routing_enabled={east=true,west=true}`.
4. Review and apply the Terraform plan.
5. Verify an authenticated request succeeds through the global hostname.
6. Preserve post-restoration routing, health, queue, alarm, and deployment evidence.

## Emergency cleanup

If validation is interrupted after a routing mutation, immediately restore both records:

```bash
terraform -chdir=infra plan \
  -var-file="$TFVARS_FILE" \
  -var='site_routing_enabled={east=true,west=true}' \
  -out=restore-routing.tfplan

terraform -chdir=infra apply restore-routing.tfplan
```

The MR-009D4 harness installs an exit trap that attempts this restoration automatically. Operators must still inspect its evidence and verify the deployed state.

## Invariants

- Never disable both sites.
- Routing isolation does not reassign existing work.
- Do not mutate `ownerRegion`, outbox records, or queue messages.
- Do not use infrastructure rollback to reverse application data.
- Do not treat direct reachability of an isolated site as a failure; only global routing is being isolated.
