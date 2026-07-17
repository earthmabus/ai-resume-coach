# Regional Isolation and Recovery Runbook

## Isolate

1. Identify the affected site and confirm the other site is healthy.
2. Set that site's `site_routing_enabled` value to `false`.
3. Plan, review, and apply the Route 53 record removal.
4. Confirm global traffic reaches the remaining site.
5. Preserve logs, alarms, traces, and deployment identifiers.

## Recover

1. Correct or roll back the isolated site.
2. Validate all regional health endpoints directly.
3. Confirm queues, DLQs, DynamoDB access, alarms, and synthetics are healthy.
4. Set the site's routing value back to `true`.
5. Plan, apply, and observe traffic before closing the incident.

Never disable both sites. Do not use infrastructure rollback to reverse application data changes.
