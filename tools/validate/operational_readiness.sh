#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'EOF'
Usage: tools/validate/operational_readiness.sh [COMMAND] [OPTIONS]

Purpose:
  Evaluate multi-site operational readiness and produce evidence.

Environment variables:
  AWS_PROFILE
      Optional. List values with: aws configure list-profiles

  EVIDENCE_ROOT
      Optional evidence destination; defaults under the repository.

Safety:
  --help performs no validation, file creation, AWS calls, or mutations.
EOF
}

case "${1:-}" in -h|--help) show_help; exit 0 ;; esac

source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/multi_site.sh"

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

python "$ROOT_DIR/tools/validate/operational_readiness.py" "${args[@]}" \
  | tee "$EVIDENCE_DIR/report.stdout.json"

record "PASSED: multi-site operational-readiness preflight"
printf '%s\n' "$EVIDENCE_DIR"
