# Shared Foundation Change Plan

## Objective

Make the shared-foundation boundary executable in Terraform without changing deployed AWS resource identities.

## Included changes

- Add `infra/modules/shared_foundation`.
- Move shared identity, notification, and MRSC data resources into the module.
- Add root `shared_foundation.tf` composition.
- Add state-preserving `moved.tf` declarations.
- Rewire regional sites, security, observability, and outputs to consume module contracts.
- Update Terraform tests to assert module ownership.

## Required validation

1. `terraform fmt -recursive -check`
2. `terraform validate`
3. `terraform test`
4. `terraform plan -out=tfplan`
5. Confirm zero destroys and zero replacements for all moved resources.
6. Apply only the reviewed saved plan.
7. Run regional runtime validation.
8. Run a post-apply no-drift plan.

## Release blockers

- Any Cognito user-pool replacement.
- Any DynamoDB table replacement.
- Any removal of the MRSC replica or witness.
- Any activation of global routing or paid overlays.
