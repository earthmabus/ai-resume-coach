# Multi-Site Deployment Runbook

1. Run formatting, validation, tests, and plan review.
2. Keep global routing disabled during the first infrastructure deployment.
3. Deploy west and verify `/health`, `/health/live`, and `/health/ready`.
4. Confirm the expected deployment ID and review west alarms and logs.
5. Deploy east and repeat the same checks.
6. Enable global routing, Route 53 health checks, WAF, dashboard, alarms, and synthetics.
7. Set `production_readiness_enforced = true` and confirm the plan succeeds.
8. Apply and verify the shared API hostname from multiple locations.
9. Preserve the plan, deployment ID, validation output, and smoke-test evidence.

Rollback the affected Region before changing the healthy Region.
