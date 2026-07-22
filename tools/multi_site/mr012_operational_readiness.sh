#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/common.sh"

for cmd in aws terraform python; do
  require_cmd "$cmd"
done

new_evidence_dir "mr012"
record "MR-012 non-mutating operational-readiness preflight"

args=(
  --infra-dir "$INFRA_DIR"
  --report "$EVIDENCE_DIR/report.json"
)
[[ -n "${AWS_PROFILE:-}" ]] && args+=(--aws-profile "$AWS_PROFILE")

python "$ROOT_DIR/tools/multi_site/mr012_operational_readiness.py" "${args[@]}" \
  | tee "$EVIDENCE_DIR/report.stdout.json"

record "PASSED: multi-site operational-readiness preflight"
printf '%s\n' "$EVIDENCE_DIR"
