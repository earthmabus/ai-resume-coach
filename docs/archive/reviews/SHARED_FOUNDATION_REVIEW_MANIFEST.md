# Shared Foundation Review Package

## Contents

- Architecture decision package under `docs/architecture/decisions/platform-layers/`.
- Proposed Terraform module under `infra/modules/shared_foundation/`.
- Root composition in `infra/shared_foundation.tf`.
- State-preserving address moves in `infra/moved.tf`.
- Rewired regional, security, observability, and output references.
- Updated Terraform contract tests.

## Safety posture

This is a review package, not an authorization to apply. The module refactor is intended to preserve all deployed AWS resources through Terraform `moved` blocks.

Before merge or apply, run in the real repository:

```bash
cd infra
terraform fmt -recursive
terraform validate
terraform test
terraform plan -input=false -out=tfplan
terraform show -no-color tfplan > tfplan.txt
```

Release blockers:

- Any destroy or replacement of Cognito resources.
- Any destroy or replacement of the DynamoDB MRSC table.
- Any change removing the us-west-2 strong replica or us-east-2 witness.
- Any enabling of global routing, Route 53 health checks, WAF, alarms, dashboards, or synthetics.

## Environment limitation

Terraform is not installed in the artifact-generation environment, so Terraform formatting, validation, tests, and planning could not be executed here. Those validations are intentionally required before this package is merged or applied.
