#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/tools/lib/multi_site.sh"

require_cmd terraform
require_cmd jq
require_cmd aws

new_evidence_dir "ms020-validate"
terraform -chdir="$INFRA_DIR" output -json > "$EVIDENCE_DIR/terraform-outputs.json"

contract="$(jq -c '.document_replication.value // empty' "$EVIDENCE_DIR/terraform-outputs.json")"
[[ -n "$contract" ]] || { echo "document_replication Terraform output is missing" >&2; exit 1; }

echo "$contract" | jq -e '
  .enabled == true and
  .mode == "BIDIRECTIONAL_CRR" and
  .east.status == "ENABLED" and
  .west.status == "ENABLED" and
  .existing_objects == false and
  .rtc_enabled == false
' >/dev/null

east_bucket="$(echo "$contract" | jq -r '.east.bucket_name')"
west_bucket="$(echo "$contract" | jq -r '.west.bucket_name')"

aws_args=()
if [[ -n "${AWS_PROFILE:-}" ]]; then
  aws_args=(--profile "$AWS_PROFILE")
fi

aws "${aws_args[@]}" --region us-east-1 s3api get-bucket-versioning \
  --bucket "$east_bucket" > "$EVIDENCE_DIR/east-versioning.json"
aws "${aws_args[@]}" --region us-west-2 s3api get-bucket-versioning \
  --bucket "$west_bucket" > "$EVIDENCE_DIR/west-versioning.json"
aws "${aws_args[@]}" --region us-east-1 s3api get-bucket-replication \
  --bucket "$east_bucket" > "$EVIDENCE_DIR/east-replication.json"
aws "${aws_args[@]}" --region us-west-2 s3api get-bucket-replication \
  --bucket "$west_bucket" > "$EVIDENCE_DIR/west-replication.json"

jq -e '.Status == "Enabled"' "$EVIDENCE_DIR/east-versioning.json" >/dev/null
jq -e '.Status == "Enabled"' "$EVIDENCE_DIR/west-versioning.json" >/dev/null
jq -e --arg destination "arn:aws:s3:::$west_bucket" '
  .ReplicationConfiguration.Rules | any(.Status == "Enabled" and .Destination.Bucket == $destination)
' "$EVIDENCE_DIR/east-replication.json" >/dev/null
jq -e --arg destination "arn:aws:s3:::$east_bucket" '
  .ReplicationConfiguration.Rules | any(.Status == "Enabled" and .Destination.Bucket == $destination)
' "$EVIDENCE_DIR/west-replication.json" >/dev/null

record "PASSED: MS-020 bidirectional document replication validated"
record "NOTICE: ordinary CRR applies to new object versions; existing objects require a separate backfill"
printf 'Evidence: %s\n' "$EVIDENCE_DIR"
