#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'HELP'
Usage: tools/resilience/activate_global_api_routing.sh {prepare|plan|apply|validate}

Activates the existing Route 53 latency-routing implementation for the two
regional APIs without depending on the retired runtime-validation tfvars file.

Environment:
  AWS_PROFILE                 Optional AWS CLI profile.
  DOMAIN_NAME                 Defaults to api.resume.michaelpopovich.com.
  HOSTED_ZONE_ID              Defaults to the project's public hosted zone.
  ROUTING_TFVARS_FILE         Generated routing tfvars file.
  ROUTING_PLAN_FILE           Saved Terraform plan used by apply.
  CONFIRM_MUTATION=YES        Required for apply.

Commands:
  prepare   Request/reuse both regional certificates and generate routing tfvars.
  plan      Create and save a routing-only Terraform plan aligned to deployed runtime values.
  apply     Apply the saved reviewed plan; requires CONFIRM_MUTATION=YES.
  validate  Validate DNS, both direct readiness endpoints, global routing, and readiness score.
HELP
}

case "${1:-}" in
  -h|--help) show_help; exit 0 ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/tools/lib/multi_site.sh"

action="${1:-plan}"
ROUTING_TFVARS_FILE="${ROUTING_TFVARS_FILE:-$INFRA_DIR/global-api-routing.generated.tfvars}"
ROUTING_PLAN_FILE="${ROUTING_PLAN_FILE:-$INFRA_DIR/.terraform-build/ms018-global-api-routing.tfplan}"
export ROUTING_TFVARS_FILE ROUTING_PLAN_FILE

require_routing_profile() {
  [[ -f "$ROUTING_TFVARS_FILE" ]] || {
    echo "Routing tfvars not found: $ROUTING_TFVARS_FILE" >&2
    echo "Run: $0 prepare" >&2
    exit 2
  }
}

case "$action" in
  prepare)
    OUTPUT_TFVARS="$ROUTING_TFVARS_FILE" \
      "$ROOT_DIR/tools/prepare/external_acm_certificates.sh"
    ;;

  plan)
    require_cmd terraform
    require_cmd jq
    require_cmd aws
    require_routing_profile

    new_evidence_dir "ms018-plan"
    mkdir -p "$(dirname "$ROUTING_PLAN_FILE")"

    prepare_deployed_runtime_alignment \
      "$EVIDENCE_DIR/deployed-runtime-alignment.json" \
      "$EVIDENCE_DIR/terraform-outputs.json"

    terraform -chdir="$INFRA_DIR" validate | tee "$EVIDENCE_DIR/terraform-validate.txt"
    terraform -chdir="$INFRA_DIR" plan \
      -input=false \
      -var-file="$ROUTING_TFVARS_FILE" \
      "${TERRAFORM_RUNTIME_ALIGNMENT_ARGS[@]}" \
      -out="$ROUTING_PLAN_FILE" | tee "$EVIDENCE_DIR/plan.txt"

    terraform -chdir="$INFRA_DIR" show -json "$ROUTING_PLAN_FILE" > "$EVIDENCE_DIR/plan.json"
    jq -r '.resource_changes[]? | select(.change.actions != ["no-op"]) | [.address, (.change.actions | join(","))] | @tsv' \
      "$EVIDENCE_DIR/plan.json" > "$EVIDENCE_DIR/changes.tsv"

    record "PASSED: MS-018 routing plan generated"
    printf 'Saved plan: %s\n' "$ROUTING_PLAN_FILE"
    printf 'Evidence: %s\n' "$EVIDENCE_DIR"
    ;;

  apply)
    require_cmd terraform
    confirm_mutation
    [[ -f "$ROUTING_PLAN_FILE" ]] || {
      echo "Saved routing plan not found: $ROUTING_PLAN_FILE" >&2
      echo "Run and review: $0 plan" >&2
      exit 2
    }

    new_evidence_dir "ms018-apply"
    terraform -chdir="$INFRA_DIR" apply -input=false "$ROUTING_PLAN_FILE" | tee "$EVIDENCE_DIR/apply.txt"
    record "PASSED: MS-018 reviewed routing plan applied"
    printf 'Evidence: %s\n' "$EVIDENCE_DIR"
    ;;

  validate)
    "$ROOT_DIR/tools/validate/global_api_edge.sh"
    "$ROOT_DIR/tools/resilience/platform_readiness.sh"
    ;;

  *) show_help >&2; exit 2 ;;
esac
