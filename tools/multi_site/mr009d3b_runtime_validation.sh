#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"

for cmd in aws terraform curl python pytest; do
  require_cmd "$cmd"
done

new_evidence_dir mr009d3b
record "MR-009D3B preflight"

python -m compileall "$ROOT_DIR/src" "$ROOT_DIR/tests" \
  > "$EVIDENCE_DIR/compileall.txt"
pytest -q "$ROOT_DIR/tests" > "$EVIDENCE_DIR/pytest.txt"
terraform -chdir="$INFRA_DIR" fmt -check -recursive \
  > "$EVIDENCE_DIR/terraform-fmt.txt"
terraform -chdir="$INFRA_DIR" validate \
  > "$EVIDENCE_DIR/terraform-validate.txt"
terraform -chdir="$INFRA_DIR" test \
  > "$EVIDENCE_DIR/terraform-test.txt"

aws_cli sts get-caller-identity > "$EVIDENCE_DIR/aws-identity.json"
regional_endpoints
health_capture east "$EAST_API"
health_capture west "$WEST_API"

cat > "$EVIDENCE_DIR/REPORT.md" <<REPORT
# MR-009D3B Runtime Evidence Report

- Timestamp: $(date -u +%FT%TZ)
- Repository validation: passed
- East liveness/readiness: captured
- West liveness/readiness: captured
- Local-owner synthetic flow: pending
- Remote-owner synthetic flow: pending

Authenticated execution requires AUTH_TOKEN, an approved validation principal,
synthetic data, EXECUTE_SYNTHETIC=YES, and CONFIRM_MUTATION=YES.
REPORT

if [[ "${EXECUTE_SYNTHETIC:-NO}" != "YES" ]]; then
  record "Preflight complete; synthetic writes not authorized"
  printf '%s\n' "$EVIDENCE_DIR"
  exit 0
fi

confirm_mutation
require_env AUTH_TOKEN
require_env SYNTHETIC_PDF
[[ -f "$SYNTHETIC_PDF" ]] || {
  echo "SYNTHETIC_PDF not found" >&2
  exit 2
}

run_flow() {
  local name="$1"
  local api="$2"
  local owner="$3"
  local corr="mr009d3b-${name}-$(date -u +%s)"
  local request_id="${corr}-request"

  curl --fail-with-body --silent --show-error \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -H "X-Correlation-Id: $corr" \
    -H "Idempotency-Key: $request_id" \
    -H "X-Validation-Owner-Region: $owner" \
    -X POST "$api/resume-upload-url" \
    -d '{"fileName":"mr009d3b-synthetic.pdf","contentType":"application/pdf"}' \
    > "$EVIDENCE_DIR/${name}-upload-url.json"

  python - "$EVIDENCE_DIR/${name}-upload-url.json" \
    "$EVIDENCE_DIR/${name}-upload.env" <<'PYCODE'
import json
import shlex
import sys

source = json.load(open(sys.argv[1]))
body = source.get("body", source)
if isinstance(body, str):
    body = json.loads(body)

values = {
    "uploadUrl": body.get("uploadUrl", ""),
    "documentKey": body.get("documentKey", body.get("key", "")),
}
with open(sys.argv[2], "w") as target:
    for key, value in values.items():
        target.write(f"{key}={shlex.quote(str(value))}\n")
PYCODE

  # shellcheck disable=SC1090
  source "$EVIDENCE_DIR/${name}-upload.env"
  [[ -n "${uploadUrl:-}" && -n "${documentKey:-}" ]] || {
    echo "Upload response did not contain uploadUrl and documentKey" >&2
    exit 4
  }

  curl --fail-with-body --silent --show-error \
    -X PUT \
    -H "Content-Type: application/pdf" \
    --data-binary "@$SYNTHETIC_PDF" \
    "$uploadUrl" \
    > "$EVIDENCE_DIR/${name}-upload-put.txt"

  curl --fail-with-body --silent --show-error \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -H "X-Correlation-Id: $corr" \
    -H "Idempotency-Key: ${request_id}-analyze" \
    -H "X-Validation-Owner-Region: $owner" \
    -X POST "$api/analyze-uploaded-resume" \
    -d "{\"documentKey\":\"$documentKey\",\"fileName\":\"mr009d3b-synthetic.pdf\",\"resumeName\":\"MR-009D3B Synthetic\"}" \
    > "$EVIDENCE_DIR/${name}-analysis-response.json"
}

run_flow east-local "$EAST_API" "${EAST_REGION:-us-east-1}"
run_flow east-to-west "$EAST_API" "${WEST_REGION:-us-west-2}"

record "Synthetic requests submitted; correlate response identifiers with logs and final state"
printf '%s\n' "$EVIDENCE_DIR"
