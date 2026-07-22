# MR-014 End-to-End Chaos Certification Runbook

## Prerequisites

Export `TFVARS_FILE`, a fresh Cognito `AUTH_TOKEN`, `SYNTHETIC_PDF`, `EXECUTE_CHAOS=YES`, and `CONFIRM_MUTATION=YES`. Optional: `WORKER_REGION` (defaults to `us-west-2`).

## Read-only gate

```bash
./tools/multi_site/mr014_chaos_validation.sh preflight
```

## Full certification

```bash
./tools/multi_site/mr014_chaos_validation.sh certify
```

The command runs the safety guard, bidirectional routing isolation, worker-backlog recovery, and final reconciliation. The final `report.json` must say `PASS` and `complete: true`.

## Individual scenarios

```bash
./tools/multi_site/mr014_chaos_validation.sh guard
./tools/multi_site/mr014_chaos_validation.sh routing-certification
./tools/multi_site/mr014_chaos_validation.sh worker-certification
./tools/multi_site/mr014_chaos_validation.sh post-recovery
```

Do not claim certification from an individual scenario. A successful mutating scenario must include restoration evidence.
