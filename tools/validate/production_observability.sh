#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/tools/lib/multi_site.sh"

require_cmd terraform
require_cmd jq
require_cmd aws
require_cmd python

new_evidence_dir "ms023-validate"
CHECKS_FILE="$EVIDENCE_DIR/checks.jsonl"
: > "$CHECKS_FILE"

add_check() {
  local name="$1"
  local status="$2"
  local detail="$3"
  local evidence="${4:-}"
  jq -cn --arg name "$name" --arg status "$status" --arg detail "$detail" --arg evidence "$evidence" \
    '{name:$name,status:$status,detail:$detail,evidence:(if $evidence == "" then null else $evidence end)}' >> "$CHECKS_FILE"
}
pass() { add_check "$1" PASS "$2" "${3:-}"; }
warn() { add_check "$1" WARN "$2" "${3:-}"; }
fail() { add_check "$1" FAIL "$2" "${3:-}"; }

terraform -chdir="$INFRA_DIR" output -json > "$EVIDENCE_DIR/terraform-outputs.json"
outputs="$EVIDENCE_DIR/terraform-outputs.json"

if jq -e '.production_observability.value.enabled == true and .production_observability.value.mode == "DASHBOARD_ALARMS_AND_SYNTHETICS"' "$outputs" >/dev/null; then
  pass production_observability_contract "Dashboard, alarms, and synthetics are enabled." terraform-outputs.json
else
  fail production_observability_contract "The MS-023 Terraform output contract is not fully enabled." terraform-outputs.json
fi

DASHBOARD_NAME="$(jq -r '.observability.value.dashboard.name' "$outputs")"
if aws_cli cloudwatch get-dashboard --dashboard-name "$DASHBOARD_NAME" > "$EVIDENCE_DIR/dashboard.json" \
    && jq -e '.DashboardBody | fromjson | .widgets | length >= 10' "$EVIDENCE_DIR/dashboard.json" >/dev/null; then
  pass dashboard "$DASHBOARD_NAME exists with the curated operations widgets." dashboard.json
else
  fail dashboard "$DASHBOARD_NAME could not be validated." dashboard.json
fi

mapfile -t ALARM_NAMES < <(jq -r '.observability.value.alarms.names[]' "$outputs")
mapfile -t EAST_ALARM_NAMES < <(printf '%s\n' "${ALARM_NAMES[@]:-}" | grep -- '-use1-' || true)
mapfile -t WEST_ALARM_NAMES < <(printf '%s\n' "${ALARM_NAMES[@]:-}" | grep -- '-usw2-' || true)

validate_regional_alarms() {
  local site="$1"
  local region="$2"
  shift 2
  local names=("$@")
  local file="$EVIDENCE_DIR/${site}-alarms.json"

  if ((${#names[@]} == 0)); then
    return 0
  fi

  aws_cli --region "$region" cloudwatch describe-alarms     --alarm-names "${names[@]}" > "$file"
}

if ((${#ALARM_NAMES[@]} == 0)); then
  fail alarms "No operational alarm names were exposed."
elif ((${#EAST_ALARM_NAMES[@]} + ${#WEST_ALARM_NAMES[@]} != ${#ALARM_NAMES[@]})); then
  fail alarms "Alarm names could not be partitioned into the east and west regional naming contracts."
else
  validate_regional_alarms east us-east-1 "${EAST_ALARM_NAMES[@]}"
  validate_regional_alarms west us-west-2 "${WEST_ALARM_NAMES[@]}"

  east_observed="$(jq '.MetricAlarms | length' "$EVIDENCE_DIR/east-alarms.json")"
  west_observed="$(jq '.MetricAlarms | length' "$EVIDENCE_DIR/west-alarms.json")"
  observed="$((east_observed + west_observed))"

  jq -n     --slurpfile east "$EVIDENCE_DIR/east-alarms.json"     --slurpfile west "$EVIDENCE_DIR/west-alarms.json"     '{MetricAlarms: (($east[0].MetricAlarms // []) + ($west[0].MetricAlarms // [])), east:$east[0], west:$west[0]}'     > "$EVIDENCE_DIR/alarms.json"

  if [[ "$east_observed" -eq "${#EAST_ALARM_NAMES[@]}"       && "$west_observed" -eq "${#WEST_ALARM_NAMES[@]}"       && "$observed" -eq "${#ALARM_NAMES[@]}" ]]; then
    pass alarms       "Validated all ${#ALARM_NAMES[@]} curated regional alarms (${#EAST_ALARM_NAMES[@]} east, ${#WEST_ALARM_NAMES[@]} west)."       alarms.json
  else
    fail alarms       "Expected ${#ALARM_NAMES[@]} alarms (${#EAST_ALARM_NAMES[@]} east, ${#WEST_ALARM_NAMES[@]} west) but AWS returned $observed ($east_observed east, $west_observed west)."       alarms.json
  fi
fi

if jq -e '.production_observability.value.notification_actions_set == true' "$outputs" >/dev/null; then
  pass alarm_notifications "At least one alarm notification action is configured."
else
  warn alarm_notifications "Alarms are active but no notification action is configured; operators must inspect CloudWatch directly."
fi

validate_canary() {
  local site="$1"
  local region="$2"
  local name="$3"
  local file="$EVIDENCE_DIR/${site}-canary.json"
  if aws_cli --region "$region" synthetics get-canary --name "$name" > "$file" \
      && jq -e '.Canary.Status.State == "RUNNING" or .Canary.Status.State == "READY"' "$file" >/dev/null; then
    pass "${site}_canary" "$name is deployed and running." "$(basename "$file")"
  else
    fail "${site}_canary" "$name is not in a running or ready state." "$(basename "$file")"
  fi
}

GLOBAL_CANARY="$(jq -r '.observability.value.synthetics.canaries.global' "$outputs")"
EAST_CANARY="$(jq -r '.observability.value.synthetics.canaries.east' "$outputs")"
WEST_CANARY="$(jq -r '.observability.value.synthetics.canaries.west' "$outputs")"
validate_canary global us-east-1 "$GLOBAL_CANARY"
validate_canary east us-east-1 "$EAST_CANARY"
validate_canary west us-west-2 "$WEST_CANARY"

python "$ROOT_DIR/tools/resilience/operations_report.py" "$CHECKS_FILE" \
  --json "$EVIDENCE_DIR/report.json" | tee "$EVIDENCE_DIR/report.txt"
status="$(jq -r '.status' "$EVIDENCE_DIR/report.json")"
if [[ "$status" == "PASS" ]]; then
  record "PASSED: MS-023 production observability validated"
else
  record "FAILED: MS-023 production observability validation"
  exit 1
fi
printf 'Evidence: %s\n' "$EVIDENCE_DIR"
