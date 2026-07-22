# MR-012 Overlay Installation

Copy this package over the repository root, preserving paths.

## Added

- `tools/multi_site/mr012_operational_readiness.py`
- `tools/multi_site/mr012_operational_readiness.sh`
- `tests/test_mr012_operational_readiness.py`
- `docs/engineering/slices/MR-012_OPERATIONAL_READINESS_AND_FINAL_RECONCILIATION.md`

## Updated

- `docs/architecture/platform-v2/MR-012_MULTI_SITE_FINAL_RECONCILIATION.md`

## Validation

```bash
python -m compileall tools/multi_site
pytest -q tests/test_mr012_operational_readiness.py
pytest -q tests
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate
```

## Runtime

Use the deployed runtime-validation profile first, then run:

```bash
./tools/multi_site/mr012_operational_readiness.sh
```
