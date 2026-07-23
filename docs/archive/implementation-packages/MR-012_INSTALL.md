# MR-012 Overlay Installation

> **Taxonomy note:** This archived guide has been normalized to the repository's
> current tooling taxonomy. The underlying MR remains historical, but all paths
> below use supported canonical locations.

Copy this package over the repository root, preserving paths.

## Added

- `tools/validate/operational_readiness.py`
- `tools/validate/operational_readiness.sh`
- `tests/test_mr012_operational_readiness.py`
- `docs/engineering/slices/MR-012_OPERATIONAL_READINESS_AND_FINAL_RECONCILIATION.md`

## Updated

- `docs/architecture/platform-v2/MR-012_MULTI_SITE_FINAL_RECONCILIATION.md`

## Validation

```bash
python -m compileall tools/validate
pytest -q tests/test_mr012_operational_readiness.py
pytest -q tests
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate
```

## Runtime

Use the deployed runtime-validation profile first, then run:

```bash
./tools/validate/operational_readiness.sh
```
