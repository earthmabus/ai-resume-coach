# MR-009D3C Option A Installation

> **Taxonomy note:** This archived guide has been normalized to the repository's
> current tooling taxonomy. The underlying MR remains historical, but all commands
> below use supported canonical paths.

## Install

Extract this ZIP from the repository root with overwrite enabled.

```bash
unzip -o ~/Downloads/ai-resume-coach-mr009d3c-global-api-edge-option-a.zip
```

## Validate repository changes

```bash
pytest -q tests
python -m compileall src tests tools
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate
terraform -chdir=infra test
./tools/validate/platform_v2_foundation.sh
```

## Request and validate external ACM certificates

```bash
export AWS_PROFILE=<profile>
./tools/prepare/external_acm_certificates.sh
```

The script creates:

```text
infra/global-api-routing.generated.tfvars
```

Review that file before using it.

## Plan and apply

```bash
terraform -chdir=infra plan \
  -input=false \
  -var-file=global-api-routing.generated.tfvars \
  -out=global-api-routing.tfplan

terraform -chdir=infra show global-api-routing.tfplan
terraform -chdir=infra apply global-api-routing.tfplan
```

## Runtime verification

```bash
TFVARS_FILE="$PWD/infra/global-api-routing.generated.tfvars" \
  ./tools/validate/global_api_edge.sh

./tools/validate/failover_runtime.sh
```
