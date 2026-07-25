#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'HELP'
Usage: tools/operations/deploy_platform.sh [OPTIONS]

Purpose:
  Build deployable artifacts, validate and apply Terraform, deploy the static
  frontend using live Terraform outputs, and verify both regional ready checks.

Options:
  --auto-approve          Apply without an interactive approval prompt
  --skip-tests            Skip Python and Terraform tests
  --skip-frontend         Apply infrastructure without deploying frontend files
  --terraform-dir DIR     Terraform root directory (default: infra)
  -h, --help              Show this help and exit without side effects

Environment variables:
  Normal Terraform TF_VAR_* variables and optional AWS_PROFILE are honored.

Examples:
  tools/operations/deploy_platform.sh
  tools/operations/deploy_platform.sh --auto-approve
HELP
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TERRAFORM_DIR="$ROOT_DIR/infra"
AUTO_APPROVE=false
RUN_TESTS=true
DEPLOY_FRONTEND=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --auto-approve) AUTO_APPROVE=true; shift ;;
    --skip-tests) RUN_TESTS=false; shift ;;
    --skip-frontend) DEPLOY_FRONTEND=false; shift ;;
    --terraform-dir)
      [[ $# -ge 2 ]] || { echo "--terraform-dir requires a value" >&2; exit 2; }
      TERRAFORM_DIR="$2"
      shift 2
      ;;
    -h|--help) show_help; exit 0 ;;
    *) echo "Unknown option: $1" >&2; show_help >&2; exit 2 ;;
  esac
done

for command in python terraform jq curl; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Required command not found: $command" >&2
    exit 1
  }
done

cd "$ROOT_DIR"

if [[ "$RUN_TESTS" == true ]]; then
  python -m compileall src tools tests
  python -m pytest -q
fi

python tools/build/pdf_dependency_layer.py
python tools/build/lambda_packages.py

terraform -chdir="$TERRAFORM_DIR" fmt -check -recursive
terraform -chdir="$TERRAFORM_DIR" init -input=false
terraform -chdir="$TERRAFORM_DIR" validate

PLAN_FILE="$TERRAFORM_DIR/tfplan"
terraform -chdir="$TERRAFORM_DIR" plan -input=false -out=tfplan

if [[ "$AUTO_APPROVE" == true ]]; then
  terraform -chdir="$TERRAFORM_DIR" apply -input=false -auto-approve tfplan
else
  terraform -chdir="$TERRAFORM_DIR" apply -input=false tfplan
fi

if [[ "$DEPLOY_FRONTEND" == true ]]; then
  "$ROOT_DIR/tools/operations/deploy_frontend.sh" --terraform-dir "$TERRAFORM_DIR"
fi

terraform -chdir="$TERRAFORM_DIR" output -json regional_api_endpoints \
  | jq -er 'to_entries[] | [.key, .value] | @tsv' \
  | while IFS=$'\t' read -r site endpoint; do
      echo "Verifying ${site} readiness: ${endpoint}/health/ready"
      curl --fail --silent --show-error --location \
        --retry 6 --retry-delay 5 --retry-all-errors \
        "${endpoint}/health/ready" >/dev/null
    done

echo "Platform deployment complete."
terraform -chdir="$TERRAFORM_DIR" output -raw frontend_url 2>/dev/null || true
echo
