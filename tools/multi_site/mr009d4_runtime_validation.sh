#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"

for cmd in aws terraform curl python pytest jq; do
  require_cmd "$cmd"
done

new_evidence_dir mr009d4
record "MR-009D4 regional isolation and recovery preflight"

if [[ "${SKIP_REPOSITORY_VALIDATION:-NO}" != "YES" ]]; then
  python -m compileall "$ROOT_DIR/src" "$ROOT_DIR/tests" > "$EVIDENCE_DIR/compileall.txt"
  pytest -q "$ROOT_DIR/tests" > "$EVIDENCE_DIR/pytest.txt"
  terraform -chdir="$INFRA_DIR" fmt -check -recursive > "$EVIDENCE_DIR/terraform-fmt.txt"
  terraform -chdir="$INFRA_DIR" validate > "$EVIDENCE_DIR/terraform-validate.txt"
  terraform -chdir="$INFRA_DIR" test > "$EVIDENCE_DIR/terraform-test.txt"
fi

aws_cli sts get-caller-identity > "$EVIDENCE_DIR/aws-identity.json"
regional_endpoints
health_capture east-before "$EAST_API"
health_capture west-before "$WEST_API"

GLOBAL_API_DOMAIN="$(jq -r '.global_api_routing.value.domain_name // empty' "$EVIDENCE_DIR/terraform-outputs.json")"
GLOBAL_ROUTING_ENABLED="$(jq -r '.global_api_routing.value.enabled // false' "$EVIDENCE_DIR/terraform-outputs.json")"
GLOBAL_API="https://${GLOBAL_API_DOMAIN}"

[[ "$GLOBAL_ROUTING_ENABLED" == "true" && -n "$GLOBAL_API_DOMAIN" ]] || {
  record "FAILED: global API routing is not enabled in the deployed Terraform state"
  exit 4
}

cat > "$EVIDENCE_DIR/REPORT.md" <<REPORT
# MR-009D4 Runtime Evidence Report

- Started: $(date -u +%FT%TZ)
- Global API: ${GLOBAL_API_DOMAIN}
- East direct health: captured
- West direct health: captured
- East isolation: pending
- East restoration: pending
- West isolation: pending
- West restoration: pending

Routing isolation removes one Route 53 latency record. It does not stop or damage
the isolated regional API. Direct regional endpoints remain available for diagnosis.
REPORT

if [[ "${EXECUTE_FAILOVER:-NO}" != "YES" ]]; then
  record "Preflight complete; routing mutations not authorized"
  printf '%s\n' "$EVIDENCE_DIR"
  exit 0
fi

confirm_mutation
require_env TFVARS_FILE
require_env AUTH_TOKEN
require_env SYNTHETIC_PDF
TFVARS_FILE="$(realpath "$TFVARS_FILE")"
[[ -f "$TFVARS_FILE" ]] || { echo "TFVARS_FILE not found" >&2; exit 2; }
[[ -f "$SYNTHETIC_PDF" ]] || { echo "SYNTHETIC_PDF not found" >&2; exit 2; }

python "$ROOT_DIR/tools/multi_site/inspect_jwt_claims.py" \
  --token "$AUTH_TOKEN" \
  --require-token-use id \
  --min-remaining-seconds "${MIN_TOKEN_LIFETIME_SECONDS:-1800}" \
  --output "$EVIDENCE_DIR/auth-token-claims.json"
record "PASSED: ID token has sufficient remaining lifetime"

http_request() {
  local step="$1" output_file="$2"
  shift 2
  local status
  status="$(curl --silent --show-error --output "$output_file" --write-out '%{http_code}' "$@")" || {
    local rc=$?
    record "FAILED: $step (curl exit $rc)"
    [[ -s "$output_file" ]] && cat "$output_file" >&2
    return "$rc"
  }
  printf '%s\n' "$status" > "${output_file}.http-status"
  if [[ ! "$status" =~ ^2 ]]; then
    record "FAILED: $step (HTTP $status)"
    [[ -s "$output_file" ]] && cat "$output_file" >&2
    return 22
  fi
  record "PASSED: $step (HTTP $status)"
}

capture_dns() {
  local label="$1"
  python - "$GLOBAL_API_DOMAIN" > "$EVIDENCE_DIR/${label}-dns.json" <<'PY'
import json, socket, sys, time
host = sys.argv[1]
addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
print(json.dumps({"host": host, "addresses": addresses, "capturedAtEpoch": int(time.time())}, indent=2))
PY
}

wait_for_global_region() {
  local expected_region="$1" label="$2"
  local timeout="${ROUTING_CONVERGENCE_TIMEOUT_SECONDS:-300}"
  local interval="${ROUTING_POLL_INTERVAL_SECONDS:-10}"
  local started now observed attempt=0
  started="$(date +%s)"
  : > "$EVIDENCE_DIR/${label}-routing-poll.jsonl"
  while true; do
    attempt=$((attempt + 1))
    now="$(date +%s)"
    local body="$EVIDENCE_DIR/${label}-global-ready-attempt-${attempt}.json"
    local status
    status="$(curl --silent --show-error --max-time 20 --output "$body" --write-out '%{http_code}' "$GLOBAL_API/health/ready" || true)"
    observed="$(jq -r '.region // empty' "$body" 2>/dev/null || true)"
    jq -n --argjson at "$now" --arg status "$status" --arg observed "$observed" \
      '{observedAtEpoch:$at,httpStatus:$status,region:$observed}' \
      >> "$EVIDENCE_DIR/${label}-routing-poll.jsonl"
    if [[ "$status" =~ ^2 && "$observed" == "$expected_region" ]]; then
      ROUTING_CONVERGENCE_SECONDS=$((now - started))
      export ROUTING_CONVERGENCE_SECONDS
      cp "$body" "$EVIDENCE_DIR/${label}-global-ready.json"
      record "PASSED: global API converged to $expected_region in ${ROUTING_CONVERGENCE_SECONDS}s"
      return 0
    fi
    if (( now - started >= timeout )); then
      record "FAILED: global API did not converge to $expected_region within ${timeout}s (last region=$observed, HTTP=$status)"
      return 7
    fi
    sleep "$interval"
  done
}

routing_changed=0
restore_both_sites() {
  local original_rc=$?
  trap - EXIT INT TERM
  if (( routing_changed == 1 )); then
    record "Safety cleanup: restoring both Route 53 routing records"
    set +e
    terraform -chdir="$INFRA_DIR" plan -input=false -lock-timeout=60s \
      -var-file="$TFVARS_FILE" -var='site_routing_enabled={east=true,west=true}' \
      -out="$EVIDENCE_DIR/safety-restore.tfplan" > "$EVIDENCE_DIR/safety-restore-plan.txt" 2>&1
    local plan_rc=$?
    if (( plan_rc == 0 )); then
      if ! validate_routing_only_plan safety-restore \
        > "$EVIDENCE_DIR/safety-restore-validation.txt" 2>&1; then
        record "CRITICAL: safety restore plan contains non-routing changes; inspect $EVIDENCE_DIR/safety-restore-validation.txt"
        set -e
        exit "$original_rc"
      fi
      terraform -chdir="$INFRA_DIR" apply -input=false "$EVIDENCE_DIR/safety-restore.tfplan" \
        > "$EVIDENCE_DIR/safety-restore-apply.txt" 2>&1
      local apply_rc=$?
      if (( apply_rc == 0 )); then
        routing_changed=0
        record "Safety cleanup completed: both routing records restored"
      else
        record "CRITICAL: safety restore apply failed; inspect $EVIDENCE_DIR/safety-restore-apply.txt"
      fi
    else
      record "CRITICAL: safety restore plan failed; inspect $EVIDENCE_DIR/safety-restore-plan.txt"
    fi
    set -e
  fi
  exit "$original_rc"
}
trap restore_both_sites EXIT INT TERM

validate_routing_only_plan() {
  local label="$1"
  local plan_file="$EVIDENCE_DIR/${label}.tfplan"
  local plan_json="$EVIDENCE_DIR/${label}-plan.json"
  local unexpected_file="$EVIDENCE_DIR/${label}-unexpected-resource-changes.txt"

  terraform -chdir="$INFRA_DIR" show -json "$plan_file" > "$plan_json"

  jq -r '
    .resource_changes[]?
    | select(.change.actions != ["no-op"])
    | .address
    | select(
        . != "module.global_edge.aws_route53_record.east_api_a[0]"
        and . != "module.global_edge.aws_route53_record.west_api_a[0]"
      )
  ' "$plan_json" > "$unexpected_file"

  if [[ -s "$unexpected_file" ]]; then
    record "FAILED: $label plan contains non-routing resource changes"
    cat "$unexpected_file" >&2
    record "Refusing apply; reconcile Terraform drift or input variables first"
    return 8
  fi

  record "PASSED: $label plan is limited to Route 53 routing records"
}

apply_routing() {
  local label="$1" routing="$2"
  terraform -chdir="$INFRA_DIR" plan -input=false -lock-timeout=60s \
    -var-file="$TFVARS_FILE" -var="site_routing_enabled=$routing" \
    -out="$EVIDENCE_DIR/${label}.tfplan" | tee "$EVIDENCE_DIR/${label}-plan.txt"

  validate_routing_only_plan "$label"

  terraform -chdir="$INFRA_DIR" apply -input=false "$EVIDENCE_DIR/${label}.tfplan" \
    | tee "$EVIDENCE_DIR/${label}-apply.txt"
  routing_changed=1
  terraform_output_json > "$EVIDENCE_DIR/${label}-terraform-outputs.json"
}

restore_routing() {
  local label="$1"
  apply_routing "$label" '{east=true,west=true}'
  routing_changed=0
  capture_dns "$label"
  record "PASSED: both regional routing records restored"
}

ensure_target_career() {
  http_request "read Target Career prerequisite through global API" \
    "$EVIDENCE_DIR/target-career-global.json" --max-time 20 \
    -H "Authorization: Bearer $AUTH_TOKEN" "$GLOBAL_API/target-career"
  local role industry
  role="$(jq -r '.roleTitle // empty' "$EVIDENCE_DIR/target-career-global.json")"
  industry="$(jq -r '.industry // empty' "$EVIDENCE_DIR/target-career-global.json")"
  [[ -n "$role" && -n "$industry" ]] || {
    record "FAILED: Target Career prerequisite is not satisfied"
    return 5
  }
}

submit_survivor_flow() {
  local label="$1"
  local expected_region="$2"
  local direct_api="$3"
  local corr="mr009d4-${label}-$(date -u +%s)"
  local request_id="${corr}-request"
  http_request "$label create upload URL through global API" "$EVIDENCE_DIR/${label}-upload-url.json" \
    --max-time 20 -H "Authorization: Bearer $AUTH_TOKEN" -H 'Content-Type: application/json' \
    -H "X-Correlation-Id: $corr" -H "Idempotency-Key: $request_id" \
    -X POST "$GLOBAL_API/resume-upload-url" \
    -d '{"fileName":"mr009d4-synthetic.pdf","contentType":"application/pdf"}'

  python - "$EVIDENCE_DIR/${label}-upload-url.json" "$EVIDENCE_DIR/${label}-upload.env" <<'PY'
import json, shlex, sys
body=json.load(open(sys.argv[1])); body=body.get("body", body)
if isinstance(body, str): body=json.loads(body)
with open(sys.argv[2], "w") as target:
    target.write("uploadUrl=" + shlex.quote(str(body.get("uploadUrl", ""))) + "\n")
    target.write("documentKey=" + shlex.quote(str(body.get("documentKey", body.get("key", "")))) + "\n")
PY
  # shellcheck disable=SC1090
  source "$EVIDENCE_DIR/${label}-upload.env"
  [[ -n "${uploadUrl:-}" && -n "${documentKey:-}" ]] || return 4

  http_request "$label upload synthetic PDF" "$EVIDENCE_DIR/${label}-upload-put.txt" \
    --max-time 60 -X PUT -H 'Content-Type: application/pdf' \
    --data-binary "@$SYNTHETIC_PDF" "$uploadUrl"

  http_request "$label submit analysis through global API" "$EVIDENCE_DIR/${label}-analysis-response.json" \
    --max-time 30 -H "Authorization: Bearer $AUTH_TOKEN" -H 'Content-Type: application/json' \
    -H "X-Correlation-Id: $corr" -H "Idempotency-Key: ${request_id}-analyze" \
    -X POST "$GLOBAL_API/analyze-uploaded-resume" \
    -d "{\"documentKey\":\"$documentKey\",\"fileName\":\"mr009d4-synthetic.pdf\",\"resumeName\":\"MR-009D4 ${label}\"}"

  local analysis_id
  analysis_id="$(jq -r '.analysisId // .body.analysisId // empty' "$EVIDENCE_DIR/${label}-analysis-response.json")"
  [[ -n "$analysis_id" ]] || return 4

  http_request "$label read analysis through global API" "$EVIDENCE_DIR/${label}-analysis-global.json" \
    --max-time 20 -H "Authorization: Bearer $AUTH_TOKEN" "$GLOBAL_API/analysis/$analysis_id"
  http_request "$label read analysis through surviving direct API" "$EVIDENCE_DIR/${label}-analysis-survivor.json" \
    --max-time 20 -H "Authorization: Bearer $AUTH_TOKEN" "$direct_api/analysis/$analysis_id"

  local global_owner survivor_owner
  global_owner="$(jq -r '.ownerRegion // empty' "$EVIDENCE_DIR/${label}-analysis-global.json")"
  survivor_owner="$(jq -r '.ownerRegion // empty' "$EVIDENCE_DIR/${label}-analysis-survivor.json")"
  [[ "$global_owner" == "$expected_region" && "$survivor_owner" == "$expected_region" ]] || {
    record "FAILED: $label owner mismatch (expected=$expected_region global=$global_owner survivor=$survivor_owner)"
    return 6
  }
  record "PASSED: $label new work is owned by surviving region $expected_region"
}

capture_dns baseline
http_request "baseline global readiness" "$EVIDENCE_DIR/baseline-global-ready.json" --max-time 20 "$GLOBAL_API/health/ready"
ensure_target_career

apply_routing isolate-east '{east=false,west=true}'
capture_dns east-isolated
wait_for_global_region "${WEST_REGION:-us-west-2}" east-isolated
submit_survivor_flow east-isolated "${WEST_REGION:-us-west-2}" "$WEST_API"
health_capture east-direct-while-isolated "$EAST_API"
health_capture west-survivor "$WEST_API"
restore_routing restore-east

apply_routing isolate-west '{east=true,west=false}'
capture_dns west-isolated
wait_for_global_region "${EAST_REGION:-us-east-1}" west-isolated
submit_survivor_flow west-isolated "${EAST_REGION:-us-east-1}" "$EAST_API"
health_capture west-direct-while-isolated "$WEST_API"
health_capture east-survivor "$EAST_API"
restore_routing restore-west

health_capture east-after "$EAST_API"
health_capture west-after "$WEST_API"
http_request "post-restoration authenticated global read" "$EVIDENCE_DIR/post-restoration-target-career.json" \
  --max-time 20 -H "Authorization: Bearer $AUTH_TOKEN" "$GLOBAL_API/target-career"

cat >> "$EVIDENCE_DIR/REPORT.md" <<REPORT

## Result

- Completed: $(date -u +%FT%TZ)
- East isolation and West survivor flow: passed
- East restoration: passed
- West isolation and East survivor flow: passed
- West restoration: passed
- Post-restoration authenticated global request: passed
REPORT

record "MR-009D4 PASSED: bidirectional routing isolation, survivor writes, and restoration verified"
printf '%s\n' "$EVIDENCE_DIR"
