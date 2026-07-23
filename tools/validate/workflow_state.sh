#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'EOF'
Usage: tools/validate/workflow_state.sh [COMMAND] [OPTIONS]

Purpose:
  Validate explicit workflow-state transitions and export evidence.

Environment variables:
  EVIDENCE_ROOT
      Optional evidence destination; defaults under the repository.

Safety:
  --help performs no validation, file creation, AWS calls, or mutations.
EOF
}

case "${1:-}" in -h|--help) show_help; exit 0 ;; esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="${EVIDENCE_DIR:-${ROOT_DIR}/evidence/mr013-${TIMESTAMP}}"
REPORT_PATH="${EVIDENCE_DIR}/workflow-state-contract.json"

mkdir -p "${EVIDENCE_DIR}"
export PYTHONPATH="${ROOT_DIR}/src:${PYTHONPATH:-}"

python "${ROOT_DIR}/tools/validate/workflow_state.py" \
  --output "${REPORT_PATH}"

echo "MR-013 workflow-state contract: PASS"
echo "${EVIDENCE_DIR}"
