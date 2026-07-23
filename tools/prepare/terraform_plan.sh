#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INFRA_DIR="${INFRA_DIR:-$ROOT_DIR/infra}"
PLAN_FILE="${PLAN_FILE:-$INFRA_DIR/tfplan}"
show_help(){ cat <<'EOF'
Usage: tools/prepare/terraform_plan.sh [--skip-validation] [--output FILE]

Purpose:
  Validate the Terraform configuration and create a real execution plan using
  explicit deployment inputs.

Options:
  --skip-validation  Do not run tools/validate/terraform.sh first.
  --output FILE      Plan destination. Default: infra/tfplan.
  -h, --help         Show help without running Terraform.

Environment variables:
  TF_VAR_deployment_id (required)
      Deployment identifier recorded by the regional applications.
      Acquire: export TF_VAR_deployment_id="$(git rev-parse HEAD)"

  TF_VAR_registration_notification_email (required)
      Approved SNS email subscriber for registration notifications.
      Inspect current subscription/topic:
        terraform -chdir=infra output -raw registration_notification_topic_arn

  INFRA_DIR (optional)
      Terraform root. Default: <repository>/infra.

  PLAN_FILE (optional)
      Default output plan path; overridden by --output.

This tool creates a plan only. It never runs terraform apply.
EOF
}
for arg in "$@"; do [[ "$arg" =~ ^(-h|--help)$ ]] && { show_help; exit 0; }; done
skip=0
while (($#)); do case "$1" in --skip-validation) skip=1; shift;; --output) PLAN_FILE="$2"; shift 2;; *) echo "Unknown option: $1" >&2; exit 2;; esac; done
: "${TF_VAR_deployment_id:?Set with: export TF_VAR_deployment_id=\"\$(git rev-parse HEAD)\"}"
: "${TF_VAR_registration_notification_email:?Set to the approved notification email}"
((skip)) || "$ROOT_DIR/tools/validate/terraform.sh"
terraform -chdir="$INFRA_DIR" plan -input=false -out="$PLAN_FILE"
printf 'Terraform plan written to %s\n' "$PLAN_FILE"
