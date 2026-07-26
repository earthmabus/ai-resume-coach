# MS-024 — Production Readiness Certification

## Purpose

MS-024 is the capstone production gate for the active-active resilience program. It does not add infrastructure. It assembles live AWS control-plane checks, Terraform contracts, and the durable MR-014 certification into one truthful ship/no-ship decision.

## Decision model

- `CERTIFIED`: every required control passes and there are no warnings.
- `CERTIFIED_WITH_EXCEPTIONS`: every required control passes, with documented non-blocking warnings.
- `NOT_CERTIFIED`: one or more required controls fail.

The tool never publishes a durable certification record while the result is `NOT_CERTIFIED`.

## Certification categories

- Architecture: approved east/west active sites.
- Reliability: routing, health, MRSC, replication, identity recovery, and fail-closed processing ownership.
- Operations: dashboard, 28 regional alarms, three running canaries, and notification coverage.
- Security: structured logging privacy controls, encryption, PITR, and Cognito WAF.
- Governance: MR-014 evidence, Terraform readiness state, and readiness enforcement.

## Commands

Read-only assessment:

```bash
./tools/resilience/activate_production_readiness_certification.sh assess
```

Publish only after all blocking controls pass:

```bash
./tools/resilience/activate_production_readiness_certification.sh certify
```

## Current expected boundary

At the MS-023 baseline, Terraform truthfully reports that Cognito WAF is missing and production-readiness enforcement is disabled. MS-024 must therefore return `NOT_CERTIFIED` until those required controls are explicitly approved, enabled, deployed, and validated. Alarm notification actions are reported as a warning rather than a blocker.

Enabling WAF may incur ongoing AWS charges and is intentionally outside this non-mutating certification slice.

## Evidence

Each run writes sanitized report artifacts beneath `evidence/ms024-assess-*` or `evidence/ms024-certify-*`:

- `report.json`
- `report.txt`
- `MS-024_PRODUCTION_READINESS_CERTIFICATION.md`
- Terraform outputs and focused AWS validation responses

The durable certification record is published to `docs/certification/MS-024_PRODUCTION_READINESS_CERTIFICATION.md` only after a passing certification run.
