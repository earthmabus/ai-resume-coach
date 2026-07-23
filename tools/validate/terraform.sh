#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INFRA_DIR="${INFRA_DIR:-$ROOT_DIR/infra}"

show_help() {
cat <<'EOF'
Usage: tools/validate/terraform.sh [--no-fmt]

Purpose:
  Run Terraform formatting, validation, and contract tests in a sanitized child
  environment so deployment-only TF_VAR values cannot contaminate tests.

Options:
  --no-fmt   Skip terraform fmt -recursive -check.
  -h, --help Show this help and exit without contacting AWS or Terraform.

Environment variables:
  INFRA_DIR
      Optional. Terraform root; defaults to <repository>/infra.
      Suggested value: export INFRA_DIR="$(pwd)/infra"

  TF_VAR_deployment_id
      Optional in the caller; removed only from Terraform test subprocesses.
      Acquire: export TF_VAR_deployment_id="$(git rev-parse HEAD)"

  TF_VAR_registration_notification_email
      Optional in the caller; removed only from Terraform test subprocesses.
      Set to the approved notification email for plan/apply operations.

Safety:
  The caller's shell environment is never changed. This command does not apply
  infrastructure and does not contact AWS beyond provider behavior in tests.
EOF
}
[[ "${1:-}" =~ ^(-h|--help)$ ]] && { show_help; exit 0; }
skip_fmt=0; [[ "${1:-}" == "--no-fmt" ]] && skip_fmt=1
command -v terraform >/dev/null || { echo 'Missing command: terraform' >&2; exit 2; }
((skip_fmt)) || terraform -chdir="$INFRA_DIR" fmt -recursive -check
terraform -chdir="$INFRA_DIR" validate
env -u TF_VAR_deployment_id -u TF_VAR_registration_notification_email \
  terraform -chdir="$INFRA_DIR" test
