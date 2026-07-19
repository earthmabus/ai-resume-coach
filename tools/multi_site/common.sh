#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INFRA_DIR="$ROOT_DIR/infra"
EVIDENCE_ROOT="${EVIDENCE_ROOT:-$ROOT_DIR/evidence}"
AWS_PROFILE_ARG=()
[[ -n "${AWS_PROFILE:-}" ]] && AWS_PROFILE_ARG=(--profile "$AWS_PROFILE")

require_cmd() {
  command -v "$1" >/dev/null || {
    echo "Missing command: $1" >&2
    exit 2
  }
}

require_env() {
  [[ -n "${!1:-}" ]] || {
    echo "Missing environment variable: $1" >&2
    exit 2
  }
}

aws_cli() {
  aws "${AWS_PROFILE_ARG[@]}" "$@"
}

new_evidence_dir() {
  local prefix="$1"
  local stamp
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  EVIDENCE_DIR="$EVIDENCE_ROOT/${prefix}-${stamp}"
  mkdir -p "$EVIDENCE_DIR"
  export EVIDENCE_DIR
}

record() {
  printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*" |
    tee -a "$EVIDENCE_DIR/execution.log"
}

confirm_mutation() {
  [[ "${CONFIRM_MUTATION:-NO}" == "YES" ]] || {
    echo "Mutation blocked. Set CONFIRM_MUTATION=YES after authorization." >&2
    exit 3
  }
}

terraform_output_json() {
  terraform -chdir="$INFRA_DIR" output -json
}

regional_endpoints() {
  terraform_output_json > "$EVIDENCE_DIR/terraform-outputs.json"
  EAST_API="$(python -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["regional_api_endpoints"]["value"]["east"])' "$EVIDENCE_DIR/terraform-outputs.json")"
  WEST_API="$(python -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["regional_api_endpoints"]["value"]["west"])' "$EVIDENCE_DIR/terraform-outputs.json")"
  export EAST_API WEST_API
}

health_capture() {
  local name="$1"
  local endpoint="$2"
  curl --fail-with-body --silent --show-error --max-time 15 \
    "$endpoint/health/live" > "$EVIDENCE_DIR/${name}-live.json"
  curl --fail-with-body --silent --show-error --max-time 20 \
    "$endpoint/health/ready" > "$EVIDENCE_DIR/${name}-ready.json"
}
