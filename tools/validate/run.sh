#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
usage(){ cat <<'HELP'
Usage: tools/validate/run.sh <command> [args]
Commands:
  terraform              Run Terraform format, validation, and contract tests.
  platform               Validate the Platform V2 foundation.
  edge                   Validate global API edge behavior.
  runtime-baseline       Run the non-failover runtime baseline.
  failover-runtime       Run failover and recovery runtime validation.
  readiness              Validate operational readiness.
  workflow               Validate workflow-state behavior.
  chaos                  Run controlled chaos validation/certification.
  lambda-artifacts       Validate Lambda artifacts.
HELP
}
case "${1:-}" in
  -h|--help|'') usage; [[ -n "${1:-}" ]] || exit 2; exit 0 ;;
  terraform) shift; exec "$ROOT_DIR/tools/validate/terraform.sh" "$@" ;;
  platform) shift; exec "$ROOT_DIR/tools/validate/platform_v2_foundation.sh" "$@" ;;
  edge) shift; exec "$ROOT_DIR/tools/validate/global_api_edge.sh" "$@" ;;
  runtime-baseline) shift; exec "$ROOT_DIR/tools/validate/runtime_baseline.sh" "$@" ;;
  failover-runtime) shift; exec "$ROOT_DIR/tools/validate/failover_runtime.sh" "$@" ;;
  readiness) shift; exec "$ROOT_DIR/tools/validate/operational_readiness.sh" "$@" ;;
  workflow) shift; exec "$ROOT_DIR/tools/validate/workflow_state.sh" "$@" ;;
  chaos) shift; exec "$ROOT_DIR/tools/validate/chaos.sh" "$@" ;;
  lambda-artifacts) shift; exec python "$ROOT_DIR/tools/validate/lambda_artifacts.py" "$@" ;;
  *) echo "Unknown validate command: $1" >&2; usage >&2; exit 2 ;;
esac
