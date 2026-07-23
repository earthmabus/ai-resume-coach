#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'EOF'
Usage: tools/validate/mr009d3b_runtime.sh [COMMAND] [OPTIONS]

Purpose:
  Run MR-009D3B regional runtime validation and optional synthetic writes.

Environment variables:
  AWS_PROFILE
      Optional. List values with: aws configure list-profiles

  EVIDENCE_ROOT
      Optional evidence destination; defaults under the repository.

  EXECUTE_SYNTHETIC
      Set explicitly for the target environment.

  CONFIRM_MUTATION
      Set CONFIRM_MUTATION=YES only after authorizing AWS mutations.

  AUTH_TOKEN
      Sensitive. Acquire with: source tools/prepare/auth.sh

  SYNTHETIC_PDF
      Path to an approved synthetic PDF; verify with: test -f "$SYNTHETIC_PDF"

Safety:
  --help performs no validation, file creation, AWS calls, or mutations.
EOF
}

case "${1:-}" in -h|--help) show_help; exit 0 ;; esac
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/multi_site.sh"

for cmd in aws terraform curl python pytest jq; do
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
- Target Career prerequisite: pending
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

python "$ROOT_DIR/tools/inspect/jwt_claims.py" \
  --token "$AUTH_TOKEN" \
  --require-group "${SYNTHETIC_PLACEMENT_OVERRIDE_GROUP:-synthetic-runtime-validation}" \
  --output "$EVIDENCE_DIR/auth-token-claims.json"
record "PASSED: validation principal contains the authorized synthetic group"

[[ -f "$SYNTHETIC_PDF" ]] || {
  echo "SYNTHETIC_PDF not found" >&2
  exit 2
}

http_request() {
  local step="$1"
  local output_file="$2"
  shift 2

  local status
  status="$(curl --silent --show-error \
    --output "$output_file" \
    --write-out '%{http_code}' \
    "$@")" || {
      local curl_status=$?
      record "FAILED: $step (curl exit $curl_status)"
      [[ -s "$output_file" ]] && cat "$output_file" >&2
      exit "$curl_status"
    }

  printf '%s\n' "$status" > "${output_file}.http-status"

  if [[ ! "$status" =~ ^2 ]]; then
    record "FAILED: $step (HTTP $status)"
    [[ -s "$output_file" ]] && cat "$output_file" >&2
    exit 22
  fi

  record "PASSED: $step (HTTP $status)"
}

ensure_target_career() {
  local current_file="$EVIDENCE_DIR/target-career-east-before.json"

  http_request "read Target Career prerequisite" "$current_file" \
    --max-time 20 \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    "$EAST_API/target-career"

  local version role_title industry
  version="$(jq -r '.version // 0' "$current_file")"
  role_title="$(jq -r '.roleTitle // ""' "$current_file")"
  industry="$(jq -r '.industry // ""' "$current_file")"

  if [[ -n "$role_title" && -n "$industry" ]]; then
    record "Target Career prerequisite already satisfied (version $version)"
    return
  fi

  local payload_file="$EVIDENCE_DIR/target-career-seed-request.json"
  jq -n \
    --argjson version "$version" \
    --arg roleTitle "Software Engineering Director" \
    --arg industry "Healthcare" \
    '{version: $version, roleTitle: $roleTitle, industry: $industry}' \
    > "$payload_file"

  http_request "seed Target Career prerequisite" \
    "$EVIDENCE_DIR/target-career-east-seeded.json" \
    --max-time 20 \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -X PUT "$EAST_API/target-career" \
    --data-binary "@$payload_file"

  http_request "verify Target Career replication in West" \
    "$EVIDENCE_DIR/target-career-west-after.json" \
    --max-time 20 \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    "$WEST_API/target-career"

  local west_role west_industry
  west_role="$(jq -r '.roleTitle // ""' "$EVIDENCE_DIR/target-career-west-after.json")"
  west_industry="$(jq -r '.industry // ""' "$EVIDENCE_DIR/target-career-west-after.json")"
  [[ -n "$west_role" && -n "$west_industry" ]] || {
    record "FAILED: Target Career did not replicate to West"
    exit 5
  }

  record "Target Career prerequisite satisfied and observed in West"
}

run_flow() {
  local name="$1"
  local api="$2"
  local owner="${3:-}"
  local corr="mr009d3b-${name}-$(date -u +%s)"
  local request_id="${corr}-request"
  local -a placement_headers=()

  if [[ -n "$owner" ]]; then
    placement_headers+=(
      -H "X-Validation-Owner-Region: $owner"
    )
  fi

  http_request "$name create upload URL" \
    "$EVIDENCE_DIR/${name}-upload-url.json" \
    --max-time 20 \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -H "X-Correlation-Id: $corr" \
    -H "Idempotency-Key: $request_id" \
    -X POST "$api/resume-upload-url" \
    -d '{"fileName":"mr009d3b-synthetic.pdf","contentType":"application/pdf"}'

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
    record "FAILED: $name upload response lacked uploadUrl or documentKey"
    exit 4
  }

  http_request "$name upload synthetic PDF" \
    "$EVIDENCE_DIR/${name}-upload-put.txt" \
    --max-time 60 \
    -X PUT \
    -H "Content-Type: application/pdf" \
    --data-binary "@$SYNTHETIC_PDF" \
    "$uploadUrl"

  http_request "$name submit resume analysis" \
    "$EVIDENCE_DIR/${name}-analysis-response.json" \
    --max-time 30 \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -H "X-Correlation-Id: $corr" \
    -H "Idempotency-Key: ${request_id}-analyze" \
    "${placement_headers[@]}" \
    -X POST "$api/analyze-uploaded-resume" \
    -d "{\"documentKey\":\"$documentKey\",\"fileName\":\"mr009d3b-synthetic.pdf\",\"resumeName\":\"MR-009D3B Synthetic\"}"

  local analysis_id
  analysis_id="$(jq -r '.analysisId // .body.analysisId // empty' "$EVIDENCE_DIR/${name}-analysis-response.json")"
  [[ -n "$analysis_id" ]] || {
    record "FAILED: $name analysis response lacked analysisId"
    exit 4
  }

  http_request "$name read analysis through East" \
    "$EVIDENCE_DIR/${name}-analysis-east.json" \
    --max-time 20 \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    "$EAST_API/analysis/$analysis_id"

  http_request "$name read analysis through West" \
    "$EVIDENCE_DIR/${name}-analysis-west.json" \
    --max-time 20 \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    "$WEST_API/analysis/$analysis_id"

  local expected_owner actual_east_owner actual_west_owner
  expected_owner="${owner:-${EAST_REGION:-us-east-1}}"
  actual_east_owner="$(jq -r '.ownerRegion // empty' "$EVIDENCE_DIR/${name}-analysis-east.json")"
  actual_west_owner="$(jq -r '.ownerRegion // empty' "$EVIDENCE_DIR/${name}-analysis-west.json")"
  [[ "$actual_east_owner" == "$expected_owner" && "$actual_west_owner" == "$expected_owner" ]] || {
    record "FAILED: $name ownerRegion mismatch (expected $expected_owner, east=$actual_east_owner, west=$actual_west_owner)"
    exit 6
  }
  record "PASSED: $name ownerRegion is $expected_owner through both regional APIs"
}

ensure_target_career
run_flow east-local "$EAST_API"
run_flow east-to-west "$EAST_API" "${WEST_REGION:-us-west-2}"

record "Synthetic requests submitted and cross-region ownership verified"
printf '%s\n' "$EVIDENCE_DIR"
