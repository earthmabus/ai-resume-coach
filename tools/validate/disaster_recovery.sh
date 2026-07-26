#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/tools/lib/multi_site.sh"

MODE="${DR_VALIDATION_MODE:-assess}"
[[ "$MODE" == "assess" || "$MODE" == "exercise" ]] || {
  echo "DR_VALIDATION_MODE must be assess or exercise" >&2
  exit 2
}

require_cmd terraform
require_cmd jq
require_cmd aws
require_cmd curl
require_cmd python

new_evidence_dir "ms022-${MODE}"
CHECKS_FILE="$EVIDENCE_DIR/checks.jsonl"
: > "$CHECKS_FILE"

add_check() {
  local name="$1" status="$2" detail="$3" evidence="${4:-}"
  jq -cn --arg name "$name" --arg status "$status" --arg detail "$detail" --arg evidence "$evidence" \
    '{name:$name,status:$status,detail:$detail,evidence:(if $evidence == "" then null else $evidence end)}' >> "$CHECKS_FILE"
}

pass() { add_check "$1" PASS "$2" "${3:-}"; }
fail() { add_check "$1" FAIL "$2" "${3:-}"; }

terraform -chdir="$INFRA_DIR" output -json > "$EVIDENCE_DIR/terraform-outputs.json"
outputs="$EVIDENCE_DIR/terraform-outputs.json"

check_contract() {
  local name="$1" jq_expression="$2" detail="$3"
  if jq -e "$jq_expression" "$outputs" >/dev/null; then
    pass "$name" "$detail" "terraform-outputs.json"
  else
    fail "$name" "Terraform output contract did not satisfy: $detail" "terraform-outputs.json"
  fi
}

check_contract "global_api_routing" '.global_api_routing.value.enabled == true and .global_api_routing.value.health_checks_enabled == true' \
  "Latency routing and Route 53 health checks are enabled."
check_contract "identity_recovery" '.cognito_recovery.value.enabled == true and .cognito_recovery.value.mode == "WARM_STANDBY_RESET_REQUIRED" and .cognito_recovery.value.automated_failover == false' \
  "Warm-standby identity recovery is explicitly enabled without claiming seamless failover."
check_contract "document_replication" '.document_replication.value.enabled == true and .document_replication.value.mode == "BIDIRECTIONAL_CRR"' \
  "Bidirectional document replication is enabled."
check_contract "processing_ownership" '.processing_ownership.value.mode == "PERSISTED_OWNER_REGION" and .processing_ownership.value.worker_enforcement == "FAIL_CLOSED" and .processing_ownership.value.automatic_reassignment == false' \
  "Persisted processing ownership fails closed and does not claim automatic reassignment."

EAST_API="$(jq -r '.regional_api_endpoints.value.east' "$outputs")"
WEST_API="$(jq -r '.regional_api_endpoints.value.west' "$outputs")"
GLOBAL_DOMAIN="$(jq -r '.global_api_routing.value.domain_name' "$outputs")"

probe_health() {
  local name="$1"
  local url="$2"
  local file="$EVIDENCE_DIR/${name}.json"

  if curl --fail-with-body --silent --show-error --max-time 20 "$url" > "$file"; then
    pass "$name" "$url returned a successful health response." "$(basename "$file")"
  else
    fail "$name" "$url did not return a successful health response." "$(basename "$file")"
  fi
}

probe_health "east_live" "$EAST_API/health/live"
probe_health "east_ready" "$EAST_API/health/ready"
probe_health "west_live" "$WEST_API/health/live"
probe_health "west_ready" "$WEST_API/health/ready"
probe_health "global_ready" "https://$GLOBAL_DOMAIN/health/ready"

check_lambda() {
  local site="$1"
  local region="$2"
  local function_name="$3"
  local file="$EVIDENCE_DIR/${site}-worker.json"

  if aws_cli --region "$region" lambda get-function-configuration \
      --function-name "$function_name" > "$file" \
      && jq -e '.State == "Active" and .LastUpdateStatus == "Successful"' \
        "$file" >/dev/null; then
    pass "${site}_worker" \
      "$function_name is Active with a successful last update." \
      "$(basename "$file")"
  else
    fail "${site}_worker" \
      "$function_name is not in the expected deployable state." \
      "$(basename "$file")"
  fi
}

check_lambda east us-east-1 "$(jq -r '.regional_foundations.value.east.compute.worker.name' "$outputs")"
check_lambda west us-west-2 "$(jq -r '.regional_foundations.value.west.compute.worker.name' "$outputs")"

check_queue() {
  local site="$1"
  local region="$2"
  local url="$3"
  local file="$EVIDENCE_DIR/${site}-queue.json"

  if aws_cli --region "$region" sqs get-queue-attributes \
      --queue-url "$url" \
      --attribute-names \
        QueueArn \
        ApproximateNumberOfMessages \
        ApproximateNumberOfMessagesNotVisible > "$file"; then
    pass "${site}_processing_queue" \
      "The regional processing queue is reachable." \
      "$(basename "$file")"
  else
    fail "${site}_processing_queue" \
      "The regional processing queue could not be inspected." \
      "$(basename "$file")"
  fi
}

check_queue east us-east-1 "$(jq -r '.regional_foundations.value.east.processing_queue.url' "$outputs")"
check_queue west us-west-2 "$(jq -r '.regional_foundations.value.west.processing_queue.url' "$outputs")"

poll_replica() {
  local region="$1" bucket="$2" key="$3" attempts="${DR_REPLICATION_ATTEMPTS:-24}" delay="${DR_REPLICATION_POLL_SECONDS:-5}"
  local i
  for ((i=1; i<=attempts; i++)); do
    if aws_cli --region "$region" s3api head-object --bucket "$bucket" --key "$key" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$delay"
  done
  return 1
}

exercise_replication() {
  local direction="$1" source_region="$2" source_bucket="$3" destination_region="$4" destination_bucket="$5"
  local run_id key body source_head destination_head
  run_id="$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
  key="_dr-validation/ms022/${direction}-${run_id}.json"
  body="$EVIDENCE_DIR/${direction}-sentinel.json"
  source_head="$EVIDENCE_DIR/${direction}-source-head.json"
  destination_head="$EVIDENCE_DIR/${direction}-destination-head.json"
  jq -n --arg milestone MS-022 --arg direction "$direction" --arg runId "$run_id" \
    '{milestone:$milestone,direction:$direction,runId:$runId}' > "$body"

  if ! aws_cli --region "$source_region" s3api put-object --bucket "$source_bucket" --key "$key" --body "$body" > "$EVIDENCE_DIR/${direction}-put.json"; then
    fail "document_replication_${direction}" "Unable to create the replication sentinel in the source bucket." "${direction}-put.json"
    return
  fi

  aws_cli --region "$source_region" s3api head-object --bucket "$source_bucket" --key "$key" > "$source_head" || true
  if poll_replica "$destination_region" "$destination_bucket" "$key"; then
    aws_cli --region "$destination_region" s3api head-object --bucket "$destination_bucket" --key "$key" > "$destination_head"
    pass "document_replication_${direction}" "A newly written sentinel became readable in the peer Region." "$(basename "$destination_head")"
  else
    fail "document_replication_${direction}" "The sentinel did not become readable in the peer Region before the bounded timeout." "$(basename "$source_head")"
  fi

  aws_cli --region "$source_region" s3api delete-object --bucket "$source_bucket" --key "$key" > "$EVIDENCE_DIR/${direction}-source-delete.json" || true
  aws_cli --region "$destination_region" s3api delete-object --bucket "$destination_bucket" --key "$key" > "$EVIDENCE_DIR/${direction}-destination-delete.json" || true
}

if [[ "$MODE" == "exercise" ]]; then
  confirm_mutation
  east_bucket="$(jq -r '.document_replication.value.east.bucket_name' "$outputs")"
  west_bucket="$(jq -r '.document_replication.value.west.bucket_name' "$outputs")"
  exercise_replication east_to_west us-east-1 "$east_bucket" us-west-2 "$west_bucket"
  exercise_replication west_to_east us-west-2 "$west_bucket" us-east-1 "$east_bucket"
else
  pass "document_replication_exercise" "Skipped in assess mode; use CONFIRM_MUTATION=YES with exercise to write bounded S3 sentinels."
fi

python "$ROOT_DIR/tools/resilience/dr_validation_report.py" \
  --checks "$CHECKS_FILE" \
  --mode "$MODE" \
  --report "$EVIDENCE_DIR/report.json" | tee "$EVIDENCE_DIR/report.txt"

record "PASSED: MS-022 disaster-recovery validation completed in $MODE mode"
record "NOTICE: this drill does not inject a real regional outage or perform identity/owner transfer"
printf 'Evidence: %s\n' "$EVIDENCE_DIR"
