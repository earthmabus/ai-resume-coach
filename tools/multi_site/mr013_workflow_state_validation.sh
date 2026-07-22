#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="${EVIDENCE_DIR:-${ROOT_DIR}/evidence/mr013-${TIMESTAMP}}"
REPORT_PATH="${EVIDENCE_DIR}/workflow-state-contract.json"

mkdir -p "${EVIDENCE_DIR}"
export PYTHONPATH="${ROOT_DIR}/src:${PYTHONPATH:-}"

python "${ROOT_DIR}/tools/multi_site/mr013_workflow_state_validation.py" \
  --output "${REPORT_PATH}"

echo "MR-013 workflow-state contract: PASS"
echo "${EVIDENCE_DIR}"
