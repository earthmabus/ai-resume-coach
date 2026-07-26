#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'HELP'
Usage: tools/resilience/activate_identity_recovery.sh {plan|apply|validate}

Provisions and validates the us-west-2 warm-standby Cognito recovery pool.
This slice does not claim password replication, session continuity, or automatic
identity failover. Users restored into the standby pool must reset passwords.

Environment:
  AWS_PROFILE                 Optional AWS CLI profile.
  BASELINE_TFVARS_FILE        Existing MS-018 routing profile.
  IDENTITY_PLAN_FILE          Saved Terraform plan consumed by apply.
  CONFIRM_MUTATION=YES        Required for apply.
HELP
}

case "${1:-}" in
  -h|--help) show_help; exit 0 ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/tools/lib/multi_site.sh"

action="${1:-plan}"
BASELINE_TFVARS_FILE="${BASELINE_TFVARS_FILE:-$INFRA_DIR/global-api-routing.generated.tfvars}"
IDENTITY_PLAN_FILE="${IDENTITY_PLAN_FILE:-$INFRA_DIR/.terraform-build/ms019-identity-recovery.tfplan}"

require_baseline_profile() {
  [[ -f "$BASELINE_TFVARS_FILE" ]] || {
    echo "Baseline routing tfvars not found: $BASELINE_TFVARS_FILE" >&2
    echo "Run MS-018 prepare first so this plan preserves deployed global routing." >&2
    exit 2
  }
}

case "$action" in
  plan)
    require_cmd terraform
    require_cmd jq
    require_cmd aws
    require_baseline_profile

    new_evidence_dir "ms019-plan"
    mkdir -p "$(dirname "$IDENTITY_PLAN_FILE")"

    prepare_deployed_runtime_alignment \
      "$EVIDENCE_DIR/deployed-runtime-alignment.json" \
      "$EVIDENCE_DIR/terraform-outputs.json"

    terraform -chdir="$INFRA_DIR" validate | tee "$EVIDENCE_DIR/terraform-validate.txt"
    terraform -chdir="$INFRA_DIR" plan \
      -input=false \
      -var-file="$BASELINE_TFVARS_FILE" \
      -var='enable_cognito_recovery=true' \
      "${TERRAFORM_RUNTIME_ALIGNMENT_ARGS[@]}" \
      -out="$IDENTITY_PLAN_FILE" | tee "$EVIDENCE_DIR/plan.txt"

    terraform -chdir="$INFRA_DIR" show -json "$IDENTITY_PLAN_FILE" > "$EVIDENCE_DIR/plan.json"
    jq -r '.resource_changes[]? | select(.change.actions != ["no-op"]) | [.address, (.change.actions | join(","))] | @tsv' \
      "$EVIDENCE_DIR/plan.json" > "$EVIDENCE_DIR/changes.tsv"

    record "PASSED: MS-019 identity-recovery plan generated"
    printf 'Saved plan: %s\n' "$IDENTITY_PLAN_FILE"
    printf 'Evidence: %s\n' "$EVIDENCE_DIR"
    ;;

  apply)
    require_cmd terraform
    confirm_mutation
    [[ -f "$IDENTITY_PLAN_FILE" ]] || {
      echo "Saved identity-recovery plan not found: $IDENTITY_PLAN_FILE" >&2
      echo "Run and review: $0 plan" >&2
      exit 2
    }

    new_evidence_dir "ms019-apply"
    terraform -chdir="$INFRA_DIR" apply -input=false "$IDENTITY_PLAN_FILE" | tee "$EVIDENCE_DIR/apply.txt"
    record "PASSED: MS-019 reviewed identity-recovery plan applied"
    printf 'Evidence: %s\n' "$EVIDENCE_DIR"
    ;;

  validate)
    "$ROOT_DIR/tools/validate/identity_recovery.sh"
    "$ROOT_DIR/tools/resilience/platform_readiness.sh"
    ;;

  *) show_help >&2; exit 2 ;;
esac
