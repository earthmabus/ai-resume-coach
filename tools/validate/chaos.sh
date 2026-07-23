#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'EOF'
Usage: tools/validate/chaos.sh [COMMAND] [OPTIONS]

Purpose:
  Run MR-014 controlled-chaos certification commands.

Environment variables:
  AWS_PROFILE
      Optional. List values with: aws configure list-profiles

  EVIDENCE_ROOT
      Optional evidence destination; defaults under the repository.

  TFVARS_FILE
      Path to a complete tfvars profile. Compose with: tools/prepare/certification_profile.sh compose

  AUTH_TOKEN
      Sensitive. Acquire with: source tools/prepare/auth.sh

  SYNTHETIC_PDF
      Path to an approved synthetic PDF; verify with: test -f "$SYNTHETIC_PDF"

  CONFIRM_MUTATION
      Set CONFIRM_MUTATION=YES only after authorizing AWS mutations.

Safety:
  --help performs no validation, file creation, AWS calls, or mutations.
EOF
}

case "${1:-}" in -h|--help) show_help; exit 0 ;; esac
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/multi_site.sh"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
action="${1:-catalog}"
new_evidence_dir "mr014-${action}"
python "$ROOT_DIR/tools/validate/chaos.py" catalog --output "$EVIDENCE_DIR/catalog.json" >/dev/null

require_chaos_authorization(){ [[ "${EXECUTE_CHAOS:-NO}" == YES ]] || { echo 'Set EXECUTE_CHAOS=YES' >&2; exit 2; }; [[ "${CONFIRM_MUTATION:-NO}" == YES ]] || { echo 'Set CONFIRM_MUTATION=YES' >&2; exit 2; }; }
latest_evidence(){
  local prefix="$1"
  python - "$EVIDENCE_ROOT" "$prefix" <<'PYLATEST'
from pathlib import Path
import sys

root = Path(sys.argv[1])
prefix = sys.argv[2]
candidates = [
    path
    for path in root.glob(f"{prefix}-*")
    if path.is_dir()
]
if not candidates:
    raise SystemExit(f"No evidence directory found for prefix {prefix!r}")
print(max(candidates, key=lambda path: path.stat().st_mtime))
PYLATEST
}
write_result(){ local id="$1" status="$2" restored="$3" ev="$4" checks="$5"; python - "$EVIDENCE_DIR/results.json" "$id" "$status" "$restored" "$ev" "$checks" <<'PY'
import json,sys
p,id,status,restored,ev,checks=sys.argv[1:]
d=json.load(open(p)) if __import__('pathlib').Path(p).exists() else {'scenarios':{}}
d['scenarios'][id]={'status':status,'restored':restored=='true','evidence':ev,'checks':json.loads(checks)}
open(p,'w').write(json.dumps(d,indent=2,sort_keys=True)+'\n')
PY
}

case "$action" in
 certify)
   require_chaos_authorization; require_env TFVARS_FILE; require_env AUTH_TOKEN; require_env SYNTHETIC_PDF
   "$ROOT_DIR/tools/prepare/certification_profile.sh" validate | tee "$EVIDENCE_DIR/profile-validation.txt"
   combined="$EVIDENCE_DIR/results.json"; printf '{"scenarios":{}}\n' > "$combined"
   mkdir -p "$EVIDENCE_DIR/steps"
   for step in guard routing-certification worker-certification post-recovery; do
     step_evidence="$EVIDENCE_DIR/steps/$step"
     EVIDENCE_DIR_OVERRIDE="$step_evidence" "$0" "$step" | tee "$EVIDENCE_DIR/${step}.txt"
     step_results="$step_evidence/results.json"
     [[ -s "$step_results" ]] || { echo "Missing scenario results for $step: $step_results" >&2; exit 6; }
     python - "$combined" "$step_results" <<'PYMERGE'
import json,sys
a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2])); a['scenarios'].update(b.get('scenarios',{})); open(sys.argv[1],'w').write(json.dumps(a,indent=2,sort_keys=True)+'\n')
PYMERGE
   done
   python "$ROOT_DIR/tools/validate/chaos.py" evaluate --results "$combined" --output "$EVIDENCE_DIR/report.json"
   ;;
 catalog) cat "$EVIDENCE_DIR/catalog.json" ;;
 preflight) "$ROOT_DIR/tools/validate/operational_readiness.sh" | tee "$EVIDENCE_DIR/preflight.txt" ;;
 guard)
   "$ROOT_DIR/tools/operations/failover_recovery.sh" prove-both-disabled-rejected | tee "$EVIDENCE_DIR/guard.txt"
   ev="$(latest_evidence mr010-prove-both-disabled-rejected)"
   write_result guard-both-sites PASS false "$ev" '{"terraform_rejected_both_disabled":true}' ;;
 routing-certification)
   require_chaos_authorization; require_env TFVARS_FILE; require_env AUTH_TOKEN; require_env SYNTHETIC_PDF
   "$ROOT_DIR/tools/prepare/certification_profile.sh" validate | tee "$EVIDENCE_DIR/profile-validation.txt"
   EXECUTE_FAILOVER=YES CONFIRM_MUTATION=YES "$ROOT_DIR/tools/validate/failover_runtime.sh" | tee "$EVIDENCE_DIR/routing-certification.txt"
   ev="$(latest_evidence mr009d4)"
   grep -q 'MR-009D4 PASSED' "$ev/execution.log"
   write_result bidirectional-routing PASS true "$ev" '{"dns_convergence":true,"authenticated_survivor_writes":true,"owner_region_correct":true,"cross_region_reads":true,"routing_restored":true}' ;;
 worker-certification)
   require_chaos_authorization; require_env AUTH_TOKEN; require_env SYNTHETIC_PDF
   region="${WORKER_REGION:-us-west-2}"; site=west; [[ "$region" == "${EAST_REGION:-us-east-1}" ]] && site=east
   regional_endpoints; api="$WEST_API"; [[ "$site" == east ]] && api="$EAST_API"
   terraform_output_json > "$EVIDENCE_DIR/terraform-outputs.json"
   worker_name="$(jq -r ".regional_foundations.value.${site}.compute.worker.name" "$EVIDENCE_DIR/terraform-outputs.json")"
   queue_url="$(jq -r ".regional_foundations.value.${site}.processing_queue.url" "$EVIDENCE_DIR/terraform-outputs.json")"
   mapping_uuid="$(aws_cli lambda list-event-source-mappings --function-name "$worker_name" --region "$region" --query 'EventSourceMappings[0].UUID' --output text)"
   [[ -n "$mapping_uuid" && "$mapping_uuid" != None ]] || { echo 'Worker event source mapping not found' >&2; exit 4; }
   restored=0
   restore_worker(){ rc=$?; trap - EXIT INT TERM; if (( restored==0 )); then aws_cli lambda update-event-source-mapping --uuid "$mapping_uuid" --region "$region" --enabled > "$EVIDENCE_DIR/safety-enable.json" || true; fi; exit "$rc"; }
   trap restore_worker EXIT INT TERM
   aws_cli lambda update-event-source-mapping --uuid "$mapping_uuid" --region "$region" --no-enabled > "$EVIDENCE_DIR/disable.json"
   for _ in {1..30}; do state="$(aws_cli lambda get-event-source-mapping --uuid "$mapping_uuid" --region "$region" --query State --output text)"; [[ "$state" == Disabled ]] && break; sleep 2; done
   [[ "$state" == Disabled ]]
   corr="mr014-worker-$(date -u +%s)"; idem="$corr-request"
   curl --fail-with-body -sS -H "Authorization: Bearer $AUTH_TOKEN" -H 'Content-Type: application/json' -H "X-Correlation-Id: $corr" -H "Idempotency-Key: $idem" -X POST "$api/resume-upload-url" -d '{"fileName":"mr014-synthetic.pdf","contentType":"application/pdf"}' > "$EVIDENCE_DIR/upload-url.json"
   upload_url="$(jq -r '.uploadUrl // .body.uploadUrl' "$EVIDENCE_DIR/upload-url.json")"; document_key="$(jq -r '.documentKey // .body.documentKey // .key // .body.key' "$EVIDENCE_DIR/upload-url.json")"
   curl --fail-with-body -sS -X PUT -H 'Content-Type: application/pdf' --data-binary "@$SYNTHETIC_PDF" "$upload_url" > "$EVIDENCE_DIR/upload.txt"
   body="{\"documentKey\":\"$document_key\",\"fileName\":\"mr014-synthetic.pdf\",\"resumeName\":\"MR-014 Worker Interruption\"}"
   for n in 1 2; do curl --fail-with-body -sS -H "Authorization: Bearer $AUTH_TOKEN" -H 'Content-Type: application/json' -H "X-Correlation-Id: $corr" -H "Idempotency-Key: ${idem}-analysis" -X POST "$api/analyze-uploaded-resume" -d "$body" > "$EVIDENCE_DIR/submit-${n}.json"; done
   id1="$(jq -r '.analysisId // .body.analysisId' "$EVIDENCE_DIR/submit-1.json")"; id2="$(jq -r '.analysisId // .body.analysisId' "$EVIDENCE_DIR/submit-2.json")"; [[ -n "$id1" && "$id1" == "$id2" ]]
   backlog_deadline=$(( $(date +%s) + ${BACKLOG_APPEAR_TIMEOUT_SECONDS:-120} )); visible=0; not_visible=0
   while (( $(date +%s) < backlog_deadline )); do
     aws_cli sqs get-queue-attributes \
       --queue-url "$queue_url" \
       --region "$region" \
       --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible \
       > "$EVIDENCE_DIR/backlog-latest.json"
     visible="$(jq -r '.Attributes.ApproximateNumberOfMessages // "0"' "$EVIDENCE_DIR/backlog-latest.json")"
     not_visible="$(jq -r '.Attributes.ApproximateNumberOfMessagesNotVisible // "0"' "$EVIDENCE_DIR/backlog-latest.json")"
     if (( ${visible:-0} + ${not_visible:-0} >= 1 )); then
       break
     fi
     sleep "${BACKLOG_POLL_SECONDS:-5}"
   done
   (( ${visible:-0} + ${not_visible:-0} >= 1 )) || {
     echo "Timed out waiting for worker backlog: visible=${visible:-0}, notVisible=${not_visible:-0}" >&2
     exit 5
   }
   record "PASSED: disabled worker retained a durable SQS backlog"

   aws_cli lambda update-event-source-mapping --uuid "$mapping_uuid" --region "$region" --enabled > "$EVIDENCE_DIR/enable.json"
   state=''
   for _ in {1..30}; do
     state="$(aws_cli lambda get-event-source-mapping --uuid "$mapping_uuid" --region "$region" --query State --output text)"
     [[ "$state" == Enabled ]] && break
     sleep 2
   done
   [[ "$state" == Enabled ]] || { echo "Worker event source mapping did not reach Enabled; state=$state" >&2; exit 5; }
   restored=1
   record "PASSED: worker event source mapping restored"

   deadline=$(( $(date +%s) + ${WORKFLOW_COMPLETION_TIMEOUT_SECONDS:-300} )); status=''
   while (( $(date +%s) < deadline )); do curl --fail-with-body -sS -H "Authorization: Bearer $AUTH_TOKEN" "$api/analysis/$id1" > "$EVIDENCE_DIR/analysis-latest.json"; status="$(jq -r '.status // .body.status' "$EVIDENCE_DIR/analysis-latest.json")"; [[ "$status" == completed ]] && break; sleep 5; done
   [[ "$status" == completed ]] || {
     echo "Workflow did not complete before timeout; final status=${status:-missing}" >&2
     exit 5
   }
   record "PASSED: interrupted workflow completed after worker restoration"

   for _ in {1..30}; do
     aws_cli sqs get-queue-attributes \
       --queue-url "$queue_url" \
       --region "$region" \
       --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible \
       > "$EVIDENCE_DIR/queue-drain-latest.json"
     visible="$(jq -r '.Attributes.ApproximateNumberOfMessages // "0"' "$EVIDENCE_DIR/queue-drain-latest.json")"
     not_visible="$(jq -r '.Attributes.ApproximateNumberOfMessagesNotVisible // "0"' "$EVIDENCE_DIR/queue-drain-latest.json")"
     (( ${visible:-0} + ${not_visible:-0} == 0 )) && break
     sleep 5
   done
   (( ${visible:-0} + ${not_visible:-0} == 0 )) || {
     echo "Worker queue did not drain: visible=${visible:-0}, notVisible=${not_visible:-0}" >&2
     exit 5
   }
   record "PASSED: worker queue drained"
   write_result worker-backlog PASS true "$EVIDENCE_DIR" '{"worker_disabled":true,"backlog_retained":true,"duplicate_idempotent":true,"worker_restored":true,"workflow_completed":true,"queue_drained":true}' ;;
 post-recovery)
   "$ROOT_DIR/tools/validate/operational_readiness.sh" | tee "$EVIDENCE_DIR/readiness.txt"
   require_env AUTH_TOKEN; regional_endpoints
   curl --fail-with-body -sS -H "Authorization: Bearer $AUTH_TOKEN" "$EAST_API/target-career" > "$EVIDENCE_DIR/east-target-career.json"
   curl --fail-with-body -sS -H "Authorization: Bearer $AUTH_TOKEN" "$WEST_API/target-career" > "$EVIDENCE_DIR/west-target-career.json"
   write_result post-recovery PASS false "$EVIDENCE_DIR" '{"both_regions_ready":true,"mrsc_healthy":true,"authenticated_reads":true,"restoration_clear":true}' ;;
 evaluate)
   require_env MR014_RESULTS_FILE; python "$ROOT_DIR/tools/validate/chaos.py" evaluate --results "$MR014_RESULTS_FILE" --output "$EVIDENCE_DIR/report.json" ;;
 *) echo "Usage: $0 {catalog|preflight|certify|guard|routing-certification|worker-certification|post-recovery|evaluate}" >&2; exit 2 ;;
esac
printf '%s\n' "$EVIDENCE_DIR"
