# Regional document bucket CORS fix

This overlay contains only the permanent browser-upload CORS implementation.
It intentionally does not change the outbox publisher schedule defaults.

Apply from the repository root after restoring the prior schedule experiment:

```bash
git restore -- \
  infra/variables.tf \
  infra/terraform.tfvars.example \
  infra/regional_sites.tf \
  infra/tests/regional_compute.tftest.hcl \
  infra/tests/regional_foundation.tftest.hcl

unzip -o ~/Downloads/regional-document-cors-only-fix.zip -d .
```

## Operational tooling taxonomy

Canonical commands are grouped by intent under `tools/build`, `tools/prepare`,
`tools/inspect`, `tools/validate`, `tools/operations`, and `tools/lib`.
Legacy paths remain as compatibility entrypoints during migration.

Start with:

```bash
./tools/validate/terraform.sh --help
./tools/prepare/terraform_plan.sh --help
./tools/inspect/environment.sh --help
./tools/validate/chaos.sh --help
```
