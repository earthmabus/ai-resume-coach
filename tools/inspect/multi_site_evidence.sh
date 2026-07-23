#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'EOF'
Usage: tools/inspect/multi_site_evidence.sh [COMMAND] [OPTIONS]

Purpose:
  Collect a read-only snapshot of multi-site AWS and Terraform state.

Environment variables:
  AWS_PROFILE
      Optional. List values with: aws configure list-profiles

  EVIDENCE_ROOT
      Optional evidence destination; defaults under the repository.

  DYNAMODB_TABLE_NAME
      Set explicitly for the target environment.

  EAST_REGION
      Set explicitly for the target environment.

  WEST_REGION
      Set explicitly for the target environment.

Safety:
  --help performs no validation, file creation, AWS calls, or mutations.
EOF
}

case "${1:-}" in -h|--help) show_help; exit 0 ;; esac
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/multi_site.sh"

for cmd in aws terraform curl python; do
  require_cmd "$cmd"
done

label="${1:-snapshot}"
new_evidence_dir "$label"
record "Collecting read-only multi-site evidence"

aws_cli sts get-caller-identity > "$EVIDENCE_DIR/aws-identity.json"
terraform_output_json > "$EVIDENCE_DIR/terraform-outputs.json"

set +e
terraform -chdir="$INFRA_DIR" plan -detailed-exitcode -input=false -lock=false \
  > "$EVIDENCE_DIR/no-drift.txt" 2>&1
plan_rc=$?
set -e
printf '%s\n' "$plan_rc" > "$EVIDENCE_DIR/no-drift-exit-code.txt"

regional_endpoints
health_capture east "$EAST_API"
health_capture west "$WEST_API"

if [[ -n "${DYNAMODB_TABLE_NAME:-}" ]]; then
  aws_cli dynamodb describe-table \
    --table-name "$DYNAMODB_TABLE_NAME" \
    --region "${PRIMARY_REGION:-us-east-1}" \
    > "$EVIDENCE_DIR/dynamodb-table.json"
fi

for region in "${EAST_REGION:-us-east-1}" "${WEST_REGION:-us-west-2}"; do
  safe="${region//-/_}"
  aws_cli cloudwatch describe-alarms \
    --region "$region" \
    --state-value ALARM \
    > "$EVIDENCE_DIR/${safe}-alarms-alarm.json"
  aws_cli lambda list-event-source-mappings \
    --region "$region" \
    > "$EVIDENCE_DIR/${safe}-event-source-mappings.json"
done

record "Evidence written to $EVIDENCE_DIR"
printf '%s\n' "$EVIDENCE_DIR"
