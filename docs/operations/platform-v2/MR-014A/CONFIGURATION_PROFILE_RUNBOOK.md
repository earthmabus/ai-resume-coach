# MR-014A Configuration Profile Runbook

## Purpose

Build one complete Terraform input profile for the enhanced MR-014 chaos
certification without allowing omitted variables to revert deployed runtime
controls to defaults.

## Compose

```bash
./tools/multi_site/prepare_mr014_certification.sh compose
export TFVARS_FILE="$PWD/infra/.terraform-build/mr014-certification.tfvars"
```

The command validates that the profile explicitly enables:

- global API routing;
- Route 53 health checks;
- regional outbox publisher schedules;
- synthetic placement override;
- East and West routing records.

## Reconcile the currently deployed baseline

Generate and inspect the plan:

```bash
./tools/multi_site/prepare_mr014_certification.sh plan
```

The evidence directory contains `changes.tsv` and `plan.json`. Because an
incomplete routing-only file was previously applied, the first reconciliation
may re-enable publisher schedules and synthetic placement, recreate the
validation Cognito group, and update Lambda configuration.

Apply only after review:

```bash
export CONFIRM_MUTATION=YES
./tools/multi_site/prepare_mr014_certification.sh apply
```

## Validate readiness

```bash
export TFVARS_FILE="$PWD/infra/.terraform-build/mr014-certification.tfvars"
./tools/multi_site/mr014_chaos_validation.sh preflight
```

The preflight must again report all 19 checks as PASS.

## Certification

Acquire a fresh ID token and identify a real synthetic PDF before running:

```bash
./tools/acquire_auth_token.sh
export SYNTHETIC_PDF="$PWD/path/to/test-resume.pdf"
export EXECUTE_CHAOS=YES
export CONFIRM_MUTATION=YES
./tools/multi_site/mr014_chaos_validation.sh certify
```

The certification wrapper and MR-009D4 both independently validate the
complete Terraform profile before making changes.
