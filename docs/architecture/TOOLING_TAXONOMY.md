# Operational Tooling Taxonomy

Canonical executable tools are organized by operator intent:

- `tools/build/` — construct deployable artifacts.
- `tools/prepare/` — acquire or compose prerequisites and plans.
- `tools/inspect/` — perform read-only environment and evidence inspection.
- `tools/validate/` — run deterministic repository and runtime validation.
- `tools/operations/` — perform explicit operational mutations and recovery actions.
- `tools/lib/` — provide sourced shared functions; these are not workflow entrypoints.

The taxonomy is authoritative. Legacy root-level entrypoints, the former `tools/multi_site/` tree, and the former top-level `scripts/` directory have been removed. Documentation, tests, workflows, and operator commands must use canonical paths.

Executable names describe capabilities rather than delivery milestones. Milestone identifiers remain in design, certification, and historical documents.

Every executable shell tool supports `-h` and `--help`; help must run before environment checks, file creation, AWS activity, or infrastructure mutation. Python entrypoints use `argparse` or an equivalent parser and expose `--help`.

## Category dispatchers

```bash
./tools/build/run.sh --help
./tools/prepare/run.sh --help
./tools/inspect/run.sh --help
./tools/validate/run.sh --help
./tools/operations/run.sh --help
```

Dispatchers provide discoverability. Focused entrypoints remain authoritative for CI and automation.

## Canonical commands

### Build

- `python tools/build/pdf_dependency_layer.py`
- `python tools/build/lambda_packages.py`

### Prepare

- `source tools/prepare/auth.sh`
- `tools/prepare/context_zip.sh`
- `tools/prepare/external_acm_certificates.sh`
- `tools/prepare/certification_profile.sh`
- `python tools/prepare/configuration_profile.py`
- `tools/prepare/terraform_plan.sh`

### Inspect

- `tools/inspect/environment.sh`
- `python tools/inspect/jwt_claims.py`
- `tools/inspect/multi_site_evidence.sh`

### Validate

- `tools/validate/terraform.sh`
- `tools/validate/platform_v2_foundation.sh`
- `tools/validate/global_api_edge.sh`
- `tools/validate/runtime_baseline.sh`
- `tools/validate/failover_runtime.sh`
- `tools/validate/operational_readiness.sh`
- `tools/validate/workflow_state.sh`
- `tools/validate/chaos.sh`
- `python tools/validate/lambda_artifacts.py`

### Operations

- `tools/operations/failover_recovery.sh`
- `python tools/operations/replay_outbox.py`
- `tools/operations/replay_failed_permanent.sh`
