# Multi-Site Deployment Runbook

## Preconditions

Confirm the AWS account, environment, Terraform backend/workspace, approved
role, regions, and deployment ID. Preserve the reviewed plan and pre-deployment
evidence.

## Deployment sequence

1. Run `tools/multi_site/collect_evidence.sh pre-deploy`.
2. Keep global routing unchanged during application rollout.
3. Deploy the first regional application.
4. Verify its direct `/health/live` and `/health/ready` endpoints, alarms,
   queues, mappings, and deployment ID.
5. Deploy the peer regional application.
6. Repeat direct verification.
7. Review and apply global-routing changes separately.
8. Run `tools/multi_site/collect_evidence.sh post-deploy`.

## Abort conditions

Stop if direct readiness is unhealthy, deployment IDs differ unexpectedly,
queue or DLQ depth rises, an event-source mapping is disabled, the plan changes
MRSC topology unexpectedly, or both routing sites would be disabled.

## Rollback

Roll back only the affected regional application artifact or configuration.
Do not alter the healthy peer or attempt to reverse application data.
