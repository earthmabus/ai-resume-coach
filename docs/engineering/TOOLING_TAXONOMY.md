# Operational Tooling Taxonomy

Canonical executable tools are organized by operator intent:

- `tools/build/` — construct deployable artifacts.
- `tools/prepare/` — acquire or compose prerequisites and plans.
- `tools/inspect/` — read-only environment and evidence inspection.
- `tools/validate/` — deterministic repository and runtime validation.
- `tools/operations/` — explicit operational mutations and recovery actions.
- `tools/lib/` — sourced shared functions; not workflow entrypoints.

The taxonomy is authoritative. Legacy root-level entrypoints and the former
`tools/multi_site/` tree have been removed. Documentation, tests, workflows,
and operator commands must use canonical paths.

Every executable shell tool supports `-h` and `--help`; help must run before
environment checks, file creation, AWS activity, or infrastructure mutation.
Python entrypoints use `argparse` or an equivalent parser and expose `--help`.

## Canonical commands

### Build

- `python tools/build/pdf_dependency_layer.py`
- `python tools/build/lambda_packages.py`

### Prepare

- `source tools/prepare/auth.sh`
- `tools/prepare/context_zip.sh`
- `tools/prepare/external_acm_certificates.sh`
- `tools/prepare/mr014_certification.sh`
- `python tools/prepare/mr014_tfvars.py`
- `tools/prepare/terraform_plan.sh`

### Inspect

- `tools/inspect/environment.sh`
- `python tools/inspect/jwt_claims.py`
- `tools/inspect/multi_site_evidence.sh`

### Validate

- `tools/validate/terraform.sh`
- `tools/validate/platform_v2_foundation.sh`
- `tools/validate/global_api_edge.sh`
- `tools/validate/mr009d3b_runtime.sh`
- `tools/validate/mr009d4_runtime.sh`
- `tools/validate/operational_readiness.sh`
- `tools/validate/workflow_state.sh`
- `tools/validate/chaos.sh`
- `python tools/validate/lambda_artifacts.py`

### Operations

- `tools/operations/failover_recovery.sh`
- `python tools/operations/replay_outbox.py`
