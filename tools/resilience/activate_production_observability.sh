#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'HELP'
Usage: tools/resilience/activate_production_observability.sh {plan|apply|validate}

Activates the MS-023 CloudWatch dashboard, regional operational alarms, and
three public health canaries (global, east, west). The canaries and Route 53
health checks incur ongoing AWS charges.

Environment:
  AWS_PROFILE                    Optional AWS CLI profile.
  BASELINE_TFVARS_FILE           Existing MS-018 routing profile.
  OBSERVABILITY_PLAN_FILE        Saved Terraform plan consumed by apply.
  OBSERVABILITY_ALARM_ACTIONS    Optional JSON list of alarm action ARNs.
  CONFIRM_MUTATION=YES           Required for apply.
HELP
}

case "${1:-}" in
  -h|--help) show_help; exit 0 ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/tools/lib/multi_site.sh"

action="${1:-plan}"
BASELINE_TFVARS_FILE="${BASELINE_TFVARS_FILE:-$INFRA_DIR/global-api-routing.generated.tfvars}"
OBSERVABILITY_PLAN_FILE="${OBSERVABILITY_PLAN_FILE:-$INFRA_DIR/.terraform-build/ms023-production-observability.tfplan}"
OBSERVABILITY_ALARM_ACTIONS="${OBSERVABILITY_ALARM_ACTIONS:-[]}"

require_baseline_profile() {
  [[ -f "$BASELINE_TFVARS_FILE" ]] || {
    echo "Baseline routing tfvars not found: $BASELINE_TFVARS_FILE" >&2
    exit 2
  }
  jq -e 'type == "array" and all(.[]; type == "string")' <<<"$OBSERVABILITY_ALARM_ACTIONS" >/dev/null || {
    echo "OBSERVABILITY_ALARM_ACTIONS must be a JSON string array." >&2
    exit 2
  }
}

case "$action" in
  plan)
    require_cmd terraform
    require_cmd jq
    require_cmd aws
    require_baseline_profile
    new_evidence_dir "ms023-plan"
    mkdir -p "$(dirname "$OBSERVABILITY_PLAN_FILE")"
    prepare_deployed_runtime_alignment \
      "$EVIDENCE_DIR/deployed-runtime-alignment.json" \
      "$EVIDENCE_DIR/terraform-outputs.json"
    terraform -chdir="$INFRA_DIR" validate | tee "$EVIDENCE_DIR/terraform-validate.txt"
    terraform -chdir="$INFRA_DIR" plan \
      -input=false \
      -var-file="$BASELINE_TFVARS_FILE" \
      -var='enable_cognito_recovery=true' \
      -var='enable_document_replication=true' \
      -var='enable_observability_dashboard=true' \
      -var='enable_operational_alarms=true' \
      -var='enable_synthetic_monitoring=true' \
      -var="observability_alarm_actions=$OBSERVABILITY_ALARM_ACTIONS" \
      "${TERRAFORM_RUNTIME_ALIGNMENT_ARGS[@]}" \
      -out="$OBSERVABILITY_PLAN_FILE" | tee "$EVIDENCE_DIR/plan.txt"
    terraform -chdir="$INFRA_DIR" show -json "$OBSERVABILITY_PLAN_FILE" > "$EVIDENCE_DIR/plan.json"
    jq -r '.resource_changes[]? | select(.change.actions != ["no-op"]) | [.address, (.change.actions | join(","))] | @tsv' \
      "$EVIDENCE_DIR/plan.json" > "$EVIDENCE_DIR/changes.tsv"
    record "PASSED: MS-023 production-observability plan generated"
    printf 'Saved plan: %s\nEvidence: %s\n' "$OBSERVABILITY_PLAN_FILE" "$EVIDENCE_DIR"
    ;;
  apply)
    require_cmd terraform
    confirm_mutation
    [[ -f "$OBSERVABILITY_PLAN_FILE" ]] || {
      echo "Saved plan not found: $OBSERVABILITY_PLAN_FILE" >&2
      exit 2
    }
    new_evidence_dir "ms023-apply"
    terraform -chdir="$INFRA_DIR" apply -input=false "$OBSERVABILITY_PLAN_FILE" | tee "$EVIDENCE_DIR/apply.txt"
    record "PASSED: MS-023 reviewed production-observability plan applied"
    printf 'Evidence: %s\n' "$EVIDENCE_DIR"
    ;;
  validate)
    "$ROOT_DIR/tools/validate/production_observability.sh"
    "$ROOT_DIR/tools/resilience/platform_readiness.sh"
    ;;
  *) show_help >&2; exit 2 ;;
esac
