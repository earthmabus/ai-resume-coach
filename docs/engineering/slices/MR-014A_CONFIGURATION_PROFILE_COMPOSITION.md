# MR-014A — Configuration Profile Composition and Plan-Scope Safety

## Decision

Terraform controls for global routing, Route 53 health checks, outbox publisher
schedules, and synthetic placement are independent. The unsafe plan observed
while enabling global routing was caused by applying only
`global-api-routing.generated.tfvars`; variables omitted from that file fell
back to their defaults.

MR-014A introduces an explicit certification profile composed from:

1. `infra/runtime-validation.tfvars`
2. `infra/global-api-routing.generated.tfvars`

The composed profile must explicitly preserve all four controls and both
routing records before MR-014 may mutate routing.

## Safety properties

- Routing-only input files cannot be used for MR-014 certification.
- Placeholder paths and values are rejected.
- Duplicate variable assignments across profile fragments are rejected.
- The composed profile is generated under `infra/.terraform-build/` and is not
  a new source-of-truth file.
- MR-009D4 validates the complete profile again immediately before mutation.
- Existing routing-only Terraform plan validation remains authoritative for
  each isolation and restoration step.

## Operational sequence

```bash
./tools/prepare/certification_profile.sh compose

export CONFIRM_MUTATION=YES
./tools/prepare/certification_profile.sh plan
./tools/prepare/certification_profile.sh apply

export TFVARS_FILE="$PWD/infra/.terraform-build/mr014-certification.tfvars"
./tools/validate/chaos.sh preflight
./tools/validate/chaos.sh certify
```

The reconciliation plan is intentionally reviewed before apply. It may restore
runtime-validation controls that were disabled by an earlier incomplete
variable-file application. After reconciliation, MR-009D4 requires every
isolation plan to contain only the intended Route 53 record change.
