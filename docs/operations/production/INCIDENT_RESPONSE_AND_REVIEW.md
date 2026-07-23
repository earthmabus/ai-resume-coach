# Incident Response and Review

## Severity model

| Severity | Definition | Example |
|---|---|---|
| SEV-1 | Broad loss of service, data-integrity risk, or security event requiring immediate action | Both active sites unavailable or suspected unauthorized data access |
| SEV-2 | Major capability impaired with meaningful customer impact and no acceptable workaround | Work is accepted but not processing in either region |
| SEV-3 | Partial degradation, regional impairment, or bounded customer impact | One site isolated while the survivor remains healthy |
| SEV-4 | Low-impact defect or operational anomaly | Non-urgent dashboard defect or isolated retryable failure |

## Response sequence

1. Declare the incident and assign an incident lead.
2. Record UTC start time, detection source, deployment ID, and known customer impact.
3. Stabilize before optimizing: stop unsafe change, restore routing or workers using accepted runbooks, and preserve durable records.
4. Compare east and west rather than assuming one region is authoritative.
5. Use request, correlation, work, outbox, transport, and invocation identifiers to trace affected work.
6. Communicate current impact, actions, risks, and next update time.
7. Verify recovery through customer-visible behavior, queue drain, health, alarms, and logs.
8. Capture sanitized evidence and create follow-up actions.

## Recovery proof

An API call returning success is not sufficient proof of recovery. Confirm the relevant capability:

- API: real authenticated request succeeds and 5XX returns to baseline;
- worker: workflow completes and queue age/depth decline;
- publisher: newly accepted work reaches the regional queue;
- DLQ: messages are understood and deliberately handled;
- routing: global and direct endpoints match the intended state;
- data: affected records remain internally consistent and readable.

## Post-incident review

For SEV-1 through SEV-3, capture:

- concise executive summary;
- customer and business impact;
- detection and response timeline;
- contributing technical and process factors;
- what worked and what created friction;
- whether alarms and dashboards represented real impact;
- recovery evidence;
- corrective actions with owner and target date;
- runbook, test, or architecture updates.

Avoid attributing the incident to an individual. Focus on system conditions, decisions, safeguards, and learning.
