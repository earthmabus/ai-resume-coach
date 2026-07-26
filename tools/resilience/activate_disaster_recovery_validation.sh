#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'HELP'
Usage: tools/resilience/activate_disaster_recovery_validation.sh {assess|exercise|validate}

assess    Read-only live validation of both sites and all resilience contracts.
exercise  Adds bounded bidirectional S3 replication sentinels. Requires
          CONFIRM_MUTATION=YES. It does not disable Route 53, APIs, Lambdas,
          queues, DynamoDB, or Cognito.
validate  Runs assess, the platform-readiness report, and focused local tests.

Environment:
  AWS_PROFILE                  Optional AWS CLI profile.
  CONFIRM_MUTATION=YES         Required only for exercise.
  DR_REPLICATION_ATTEMPTS      Poll attempts per replication direction (default 24).
  DR_REPLICATION_POLL_SECONDS  Seconds between polls (default 5).
HELP
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
action="${1:-assess}"

case "$action" in
  -h|--help) show_help ;;
  assess)
    DR_VALIDATION_MODE=assess "$ROOT_DIR/tools/validate/disaster_recovery.sh"
    ;;
  exercise)
    [[ "${CONFIRM_MUTATION:-NO}" == "YES" ]] || {
      echo "Mutation blocked. Set CONFIRM_MUTATION=YES after authorization." >&2
      exit 3
    }
    DR_VALIDATION_MODE=exercise CONFIRM_MUTATION=YES "$ROOT_DIR/tools/validate/disaster_recovery.sh"
    ;;
  validate)
    DR_VALIDATION_MODE=assess "$ROOT_DIR/tools/validate/disaster_recovery.sh"
    "$ROOT_DIR/tools/resilience/platform_readiness.sh"
    python -m pytest -q \
      "$ROOT_DIR/tests/tooling/test_ms017_platform_readiness.py" \
      "$ROOT_DIR/tests/tooling/test_ms022_disaster_recovery_validation.py"
    ;;
  *) show_help >&2; exit 2 ;;
esac
