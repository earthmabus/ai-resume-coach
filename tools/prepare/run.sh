#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
usage(){ cat <<'HELP'
Usage: tools/prepare/run.sh <command> [args]
Commands:
  auth                  Acquire an authentication token (source auth.sh when export is required).
  certification-profile Compose, validate, plan, or apply a certification profile.
  context               Create a sanitized repository context ZIP.
  certificates          Prepare external ACM certificates.
  terraform-plan        Validate and prepare a Terraform plan.
HELP
}
case "${1:-}" in
  -h|--help|'') usage; [[ -n "${1:-}" ]] || exit 2; exit 0 ;;
  auth) shift; exec "$ROOT_DIR/tools/prepare/auth.sh" "$@" ;;
  certification-profile) shift; exec "$ROOT_DIR/tools/prepare/certification_profile.sh" "$@" ;;
  context) shift; exec "$ROOT_DIR/tools/prepare/context_zip.sh" "$@" ;;
  certificates) shift; exec "$ROOT_DIR/tools/prepare/external_acm_certificates.sh" "$@" ;;
  terraform-plan) shift; exec "$ROOT_DIR/tools/prepare/terraform_plan.sh" "$@" ;;
  *) echo "Unknown prepare command: $1" >&2; usage >&2; exit 2 ;;
esac
