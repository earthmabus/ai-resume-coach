# MR-012 — Operational Readiness and Final Reconciliation

## Intent

Provide one non-mutating gate that proves the deployed multi-site foundation is ready before any runtime, failure, or recovery validation begins. MR-012 reconciles infrastructure intent with observable runtime state; it does not claim DR certification.

## Implemented capability

Run:

```bash
./tools/validate/operational_readiness.sh
```

The command creates `evidence/mr012-<timestamp>/report.json` and exits nonzero when a required capability is unavailable or misconfigured.

## Required checks

For each active site:

- regional `/health/ready` returns HTTP 200 from the expected region;
- the outbox-publisher EventBridge schedule exists and is `ENABLED`;
- API, worker, and outbox-publisher Lambda functions exist and are active;
- processing queue, processing DLQ, and terminal-failure DLQ exist.

For shared data:

- the ResumeAnalysis table is `ACTIVE`;
- both application replicas are `ACTIVE`;
- the configured witness and MRSC contract are reported.

## Safety

The preflight is deliberately read-only. It does not enable schedules, alter concurrency, update event-source mappings, publish messages, create users, or write application data.

## Acceptance criteria

- A healthy runtime-validation deployment returns `PASS`.
- A disabled publisher schedule returns `FAIL` and names the affected site.
- A regional health response from the wrong region returns `FAIL`.
- A missing Lambda, queue, or active table replica returns `FAIL`.
- The complete report is machine-readable and retained as evidence.

## Explicit exclusions

MR-012 does not prove failover, failback, RTO, RPO, duplicate suppression under fault, or zero-to-production rebuild. Those remain later acceptance activities.
