# Regional Isolation and Recovery Runbook

## Isolate one site

1. Confirm the peer site is directly live and ready.
2. Capture pre-change evidence.
3. Set only the affected site's `site_routing_enabled` value to `false`.
4. Review and apply the Terraform plan.
5. Verify the global hostname reaches the remaining site.
6. Preserve routing, health, alarm, queue, and deployment evidence.

## Restore one site

1. Correct or roll back the isolated application.
2. Verify direct liveness/readiness, queues, DLQs, mappings, alarms, and MRSC.
3. Set the site routing value back to `true`.
4. Review and apply the Route 53 change.
5. Observe both sites before closing the incident.

## Invariants

- Never disable both sites.
- Routing isolation does not reassign existing work.
- Do not mutate `ownerRegion`, outbox records, or queue messages.
- Do not use infrastructure rollback to reverse application data.
