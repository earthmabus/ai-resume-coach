# Multi-Site Completion Plan

## Goal

Complete the multi-site active-active program through deployed runtime evidence,
controlled failover and recovery exercises, evidence-based operational runbooks,
and final architecture reconciliation.

## Implemented foundation

The repository currently implements:

- active application sites in `us-east-1` and `us-west-2`;
- a DynamoDB multi-Region strongly consistent table with witness in `us-east-2`;
- symmetric regional HTTP APIs, Lambda functions, queues, and dead-letter queues;
- shared Cognito identity;
- transactional outbox dispatch;
- deterministic work ownership and cross-Region SQS delivery;
- runtime identity, correlation, readiness, alarms, dashboards, and synthetics;
- explicit regional routing controls and a guard against disabling both sites;
- sequential deployment and regional rollback contracts;
- bounded retry, terminal-failure, and explicit workflow-state behavior.

The remaining work validates and documents those controls. It does not introduce
a generic workflow engine, public replay API, cross-Region queue draining, or
automatic reassignment of in-flight work.

## MR-009D3B — Synthetic end-to-end runtime validation

Use `tools/multi_site/mr009d3b_runtime_validation.sh` after recording the
required authorization variables in a local environment file.

Completion requires one local-owner flow and one remote-owner flow to reach the
normal completed state through the outbox, owning-region queue, and worker.

## MR-010 — Failover and recovery validation

Use `tools/multi_site/mr010_failover_recovery.sh` for:

- east isolation and restoration;
- west isolation and restoration;
- rejection of disabling both sites;
- worker interruption, queue backlog growth, restoration, and drain;
- MRSC read/write visibility;
- regional application rollback while the peer remains healthy.

Every mutating exercise requires an explicit confirmation flag and creates
timestamped evidence.

## MR-011 — Operational runbooks

Authoritative runbooks:

- `docs/operations/platform-v2/MULTI_SITE_DEPLOYMENT_RUNBOOK.md`
- `docs/operations/platform-v2/REGIONAL_ISOLATION_AND_RECOVERY_RUNBOOK.md`
- `docs/operations/platform-v2/QUEUE_BACKLOG_AND_DLQ_RUNBOOK.md`
- `docs/operations/platform-v2/INCIDENT_EVIDENCE_COLLECTION_RUNBOOK.md`
- `docs/runbooks/OUTBOX_OPERATIONS.md`

## MR-012 — Final architecture reconciliation

The final reconciliation is recorded in
`docs/architecture/platform-v2/MR-012_MULTI_SITE_FINAL_RECONCILIATION.md`.

Runtime claims remain provisional until the generated MR-009D3B and MR-010
evidence reports contain successful observations.

## Completion criteria

The multi-site program is complete when:

- repository validation remains green;
- both sites prove correct runtime identity and readiness;
- local and cross-Region asynchronous flows complete with end-to-end correlation;
- east and west isolation/restoration exercises pass;
- queue backlog growth and drain are observed without data loss;
- MRSC visibility is demonstrated;
- a regional rollback is exercised;
- runbooks match commands actually used;
- final reconciliation records evidence and known limitations.
