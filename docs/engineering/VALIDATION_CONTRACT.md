# Validation Contract

## Principles

Validation is part of the architecture. Do not weaken tests to make a change pass unless the underlying contract was explicitly changed.

Use focused validation during development and full validation before declaring a slice complete.

## Application

From the repository root:

```bash
python -m compileall src tests
pytest -q tests
```

Report the exact test count.

## Terraform Formatting and Validation

```bash
cd infra
terraform fmt -recursive -check
terraform validate
```

When provider/module initialization is required, use the repository's established initialization flow. Do not alter backends or apply infrastructure merely to run static validation.

## Focused Terraform Tests

Run each changed Terraform test directly, for example:

```bash
terraform test -filter=tests/<changed-file>.tftest.hcl
```

Report each run name and result.

## Full Platform Validation

From the repository root:

```bash
./tools/validate_platform_v2_foundation.sh
```

The known checkpoint reported:

```text
Success! 28 passed, 0 failed.
Platform V2 multi-site production readiness validation passed.
```

Treat that as historical evidence, not a guaranteed current result.

## Prohibited Validation Actions

Unless explicitly requested:

- do not run `terraform apply`
- do not deploy
- do not modify production resources
- do not commit or push
- do not bypass or delete failing tests
- do not expose secrets in logs or reports
