#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/tools/lib/multi_site.sh"

require_cmd terraform
require_cmd jq
require_cmd aws

new_evidence_dir "ms021-validate"
terraform -chdir="$INFRA_DIR" output -json > "$EVIDENCE_DIR/terraform-outputs.json"

contract="$(jq -c '.processing_ownership.value // empty' "$EVIDENCE_DIR/terraform-outputs.json")"
[[ -n "$contract" ]] || { echo "processing_ownership Terraform output is missing" >&2; exit 1; }

echo "$contract" | jq -e '
  .mode == "PERSISTED_OWNER_REGION" and
  .authoritative_field == "ownerRegion" and
  .worker_enforcement == "FAIL_CLOSED" and
  .automatic_reassignment == false and
  .cross_region_queue_drain == false and
  (.split_brain_protection | index("conditional-owner-claim") != null)
' >/dev/null

outputs="$EVIDENCE_DIR/terraform-outputs.json"
east_worker="$(jq -r '.regional_foundations.value.east.compute.worker.name' "$outputs")"
west_worker="$(jq -r '.regional_foundations.value.west.compute.worker.name' "$outputs")"

aws_args=()
if [[ -n "${AWS_PROFILE:-}" ]]; then
  aws_args=(--profile "$AWS_PROFILE")
fi

aws "${aws_args[@]}" --region us-east-1 lambda get-function-configuration \
  --function-name "$east_worker" > "$EVIDENCE_DIR/east-worker.json"
aws "${aws_args[@]}" --region us-west-2 lambda get-function-configuration \
  --function-name "$west_worker" > "$EVIDENCE_DIR/west-worker.json"

jq -e '.State == "Active" and .LastUpdateStatus == "Successful"' "$EVIDENCE_DIR/east-worker.json" >/dev/null
jq -e '.State == "Active" and .LastUpdateStatus == "Successful"' "$EVIDENCE_DIR/west-worker.json" >/dev/null

record "PASSED: MS-021 deterministic processing ownership validated"
record "NOTICE: ownership transfer is controlled and manual; automatic reassignment and cross-region queue draining remain out of scope"
printf 'Evidence: %s\n' "$EVIDENCE_DIR"
