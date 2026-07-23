#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'EOF'
Usage: tools/prepare/certification_profile.sh [COMMAND] [OPTIONS]

Purpose:
  Compose, validate, plan, or apply the MR-014 certification profile.

Environment variables:
  RUNTIME_TFVARS_FILE
      Set explicitly for the target environment.

  ROUTING_TFVARS_FILE
      Set explicitly for the target environment.

  MR014_CERTIFICATION_TFVARS_FILE
      Set explicitly for the target environment.

  TFVARS_FILE
      Path to a complete tfvars profile. Compose with: tools/prepare/certification_profile.sh compose

  CONFIRM_MUTATION
      Set CONFIRM_MUTATION=YES only after authorizing AWS mutations.

  EVIDENCE_ROOT
      Optional evidence destination; defaults under the repository.

Safety:
  --help performs no validation, file creation, AWS calls, or mutations.
EOF
}

case "${1:-}" in -h|--help) show_help; exit 0 ;; esac
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/multi_site.sh"

action="${1:-compose}"
require_cmd python
if [[ "$action" != "compose" && "$action" != "validate" ]]; then
  require_cmd terraform
  require_cmd jq
fi
new_evidence_dir "mr014a-${action}"
RUNTIME_TFVARS_FILE="${RUNTIME_TFVARS_FILE:-$INFRA_DIR/runtime-validation.tfvars}"
ROUTING_TFVARS_FILE="${ROUTING_TFVARS_FILE:-$INFRA_DIR/global-api-routing.generated.tfvars}"
MR014_CERTIFICATION_TFVARS_FILE="${MR014_CERTIFICATION_TFVARS_FILE:-$INFRA_DIR/.terraform-build/mr014-certification.tfvars}"

compose_profile() {
  python "$ROOT_DIR/tools/prepare/configuration_profile.py" compose \
    --input "$RUNTIME_TFVARS_FILE" \
    --input "$ROUTING_TFVARS_FILE" \
    --output "$MR014_CERTIFICATION_TFVARS_FILE" \
    --report "$EVIDENCE_DIR/profile-validation.json"
  cp "$MR014_CERTIFICATION_TFVARS_FILE" "$EVIDENCE_DIR/mr014-certification.tfvars"
  record "PASSED: complete MR-014 certification profile composed"
}

case "$action" in
  compose)
    compose_profile
    printf 'export TFVARS_FILE=%q\n' "$MR014_CERTIFICATION_TFVARS_FILE"
    ;;
  plan|apply)
    compose_profile
    terraform -chdir="$INFRA_DIR" plan -input=false \
      -var-file="$MR014_CERTIFICATION_TFVARS_FILE" \
      -out="$EVIDENCE_DIR/reconcile.tfplan" | tee "$EVIDENCE_DIR/plan.txt"
    terraform -chdir="$INFRA_DIR" show -json "$EVIDENCE_DIR/reconcile.tfplan" > "$EVIDENCE_DIR/plan.json"
    jq -r '.resource_changes[]? | select(.change.actions != ["no-op"]) | [.address, (.change.actions|join(","))] | @tsv' \
      "$EVIDENCE_DIR/plan.json" > "$EVIDENCE_DIR/changes.tsv"
    record "PASSED: reconciliation plan generated with complete input profile"
    if [[ "$action" == apply ]]; then
      [[ "${CONFIRM_MUTATION:-NO}" == YES ]] || { echo 'Set CONFIRM_MUTATION=YES to apply reconciliation' >&2; exit 2; }
      terraform -chdir="$INFRA_DIR" apply -input=false "$EVIDENCE_DIR/reconcile.tfplan" | tee "$EVIDENCE_DIR/apply.txt"
      record "PASSED: complete MR-014 certification baseline applied"
    fi
    printf 'export TFVARS_FILE=%q\n' "$MR014_CERTIFICATION_TFVARS_FILE"
    ;;
  validate)
    require_env TFVARS_FILE
    python "$ROOT_DIR/tools/prepare/configuration_profile.py" validate --file "$TFVARS_FILE" --report "$EVIDENCE_DIR/profile-validation.json"
    record "PASSED: TFVARS_FILE is a complete MR-014 certification profile"
    ;;
  *) echo "Usage: $0 {compose|plan|apply|validate}" >&2; exit 2 ;;
esac
printf '%s\n' "$EVIDENCE_DIR"
