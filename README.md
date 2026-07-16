# MR-005A — Isolate Lambda Deployment Packages

This bundle introduces per-Lambda source directories, deterministic staging,
and one Terraform archive per Lambda.

## Copy replacements

Copy all paths from this directory into the repository root, preserving paths.

## Build and test

```bash
python tools/build_lambda_packages.py
python -m compileall src tests tools
pytest -q tests/test_lambda_packages.py
pytest -q tests
```

## Terraform

```bash
cd infra
terraform fmt -recursive
terraform validate
terraform plan -input=false -out=tfplan-mr005a
```

The compatibility modules at `src/handler.py`, `src/worker.py`,
`src/outbox_publisher_handler.py`, and
`src/registration_notification/handler.py` deliberately alias the new source
modules. This preserves existing tests and local imports while the generated
Lambda packages deploy only the new `src/lambdas/...` handlers.
