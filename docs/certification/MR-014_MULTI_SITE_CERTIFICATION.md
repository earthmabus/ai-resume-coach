# MR-014 Multi-Site Certification Record

## Decision

**PASS — certified July 22, 2026.**

The AI Resume Coach Platform V2 multi-site implementation satisfied every required MR-014 scenario and returned to a reconciled healthy state.

## Certified deployment

| Attribute | Value |
|---|---|
| Certification run | `mr014-certify-20260722T124522Z` |
| Deployment ID | `9fd780e1583637c5848ab21c5e38a3cf56e995c9` |
| Active sites | `us-east-1`, `us-west-2` |
| MRSC witness | `us-east-2` |
| Final result | `PASS` |
| Scenario summary | 4 executed, 4 passed, 0 failed |
| Post-recovery readiness | 19 passed, 0 failed, 0 warnings |

## Certified scenarios

### 1. Both-sites-disabled safety guard

Terraform rejected a configuration that disabled both global routing records.

### 2. Bidirectional routing isolation

For each active site independently:

- the intended Route 53 routing record was removed;
- the global endpoint converged to the surviving region;
- an authenticated uploaded-resume workflow was accepted;
- new work was owned by the surviving region;
- the workflow was readable through the global and surviving direct APIs;
- the removed routing record was restored.

### 3. Worker interruption and recovery

- the selected worker event-source mapping was disabled;
- a workflow was submitted twice with one idempotency key;
- durable SQS backlog was observed;
- the mapping was restored and confirmed `Enabled`;
- one workflow reached `completed`;
- the processing queue drained;
- no duplicate workflow was created.

### 4. Post-recovery reconciliation

- both regional readiness endpoints passed;
- authenticated reads passed;
- the DynamoDB table and both active replicas were healthy;
- the MRSC witness contract was present;
- no unresolved restoration remained.

## Evidence handling

The raw execution directories remain local operational evidence and are intentionally not copied wholesale into source control. They may contain account identifiers, temporary upload material, presigned URLs, or other environment-specific data.

Authoritative local paths from the successful run were:

- `evidence/mr014-certify-20260722T124522Z/report.json`
- `evidence/mr009d4-20260722T124535Z/`
- `evidence/mr012-20260722T125205Z/`

This document is the durable, sanitized certification record.

## Certified claim

The platform can continue accepting authenticated work through the surviving active site during bounded routing isolation, preserve deterministic ownership and replicated reads, retain queued work during a worker-consumer interruption, resume processing after restoration, and return to a healthy reconciled state.

## Limitations

This certification does not assert automatic ownership reassignment, cross-Region queue draining, terminal-failure replay, zero interruption for in-flight work, contractual RTO/RPO, full production-readiness controls, or recovery from account-wide or provider-wide failure.

## Change control

Changes to routing, ownership, idempotency, outbox dispatch, worker state transitions, regional queue mapping, MRSC topology, or restoration logic must preserve the MR-014 contract. Re-run MR-014 after material changes to those areas.
