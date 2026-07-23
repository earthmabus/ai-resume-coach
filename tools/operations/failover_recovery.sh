#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'EOF'
Usage: tools/operations/failover_recovery.sh [COMMAND] [OPTIONS]

Purpose:
  Exercise controlled regional failover and recovery operations.

Environment variables:
  AWS_PROFILE
      Optional. List values with: aws configure list-profiles

  EVIDENCE_ROOT
      Optional evidence destination; defaults under the repository.

  TFVARS_FILE
      Path to a complete tfvars profile. Compose with: tools/prepare/mr014_certification.sh compose

  EXECUTE_FAILOVER
      Set explicitly for the target environment.

  CONFIRM_MUTATION
      Set CONFIRM_MUTATION=YES only after authorizing AWS mutations.

  AUTH_TOKEN
      Sensitive. Acquire with: source tools/prepare/auth.sh

  SYNTHETIC_PDF
      Path to an approved synthetic PDF; verify with: test -f "$SYNTHETIC_PDF"

Safety:
  --help performs no validation, file creation, AWS calls, or mutations.
EOF
}

case "${1:-}" in -h|--help) show_help; exit 0 ;; esac
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/multi_site.sh"

for cmd in aws terraform curl python; do
  require_cmd "$cmd"
done

action="${1:-help}"
new_evidence_dir "mr010-${action}"
regional_endpoints
health_capture east "$EAST_API"
health_capture west "$WEST_API"

case "$action" in
  prove-both-disabled-rejected)
    set +e
    terraform -chdir="$INFRA_DIR" plan -input=false -lock=false \
      -var='site_routing_enabled={east=false,west=false}' \
      > "$EVIDENCE_DIR/plan.txt" 2>&1
    rc=$?
    set -e
    [[ "$rc" -ne 0 ]] || {
      echo "Unsafe plan unexpectedly succeeded" >&2
      exit 5
    }
    record "Terraform rejected disabling both sites"
    ;;

  isolate-east|isolate-west|restore-east|restore-west)
    confirm_mutation
    require_env TFVARS_FILE
    [[ -f "$TFVARS_FILE" ]] || {
      echo "TFVARS_FILE not found" >&2
      exit 2
    }

    case "$action" in
      isolate-east) routing='{east=false,west=true}' ;;
      isolate-west) routing='{east=true,west=false}' ;;
      restore-east|restore-west) routing='{east=true,west=true}' ;;
    esac

    terraform -chdir="$INFRA_DIR" plan \
      -input=false \
      -var-file="$TFVARS_FILE" \
      -var="site_routing_enabled=$routing" \
      -out="$EVIDENCE_DIR/plan.tfplan" |
      tee "$EVIDENCE_DIR/plan.txt"

    terraform -chdir="$INFRA_DIR" apply \
      -input=false \
      "$EVIDENCE_DIR/plan.tfplan" |
      tee "$EVIDENCE_DIR/apply.txt"

    sleep 30
    health_capture east-after "$EAST_API" || true
    health_capture west-after "$WEST_API" || true
    record "$action applied"
    ;;

  disable-worker|enable-worker)
    confirm_mutation
    require_env EVENT_SOURCE_MAPPING_UUID
    require_env WORKER_REGION

    operation="disable"
    [[ "$action" == "enable-worker" ]] && operation="enable"

    aws_cli lambda "${operation}-event-source-mapping" \
      --uuid "$EVENT_SOURCE_MAPPING_UUID" \
      --region "$WORKER_REGION" \
      > "$EVIDENCE_DIR/mapping-${operation}.json"

    record "$action completed"
    ;;

  snapshot)
    aws_cli sts get-caller-identity > "$EVIDENCE_DIR/aws-identity.json"
    terraform_output_json > "$EVIDENCE_DIR/terraform-outputs.json"
    record "Read-only MR-010 snapshot complete"
    ;;

  *)
    cat <<'USAGE'
Usage: mr010_failover_recovery.sh ACTION

Actions:
  snapshot
  prove-both-disabled-rejected
  isolate-east
  restore-east
  isolate-west
  restore-west
  disable-worker
  enable-worker

Mutations require CONFIRM_MUTATION=YES and the documented environment values.
USAGE
    ;;
esac

printf '%s\n' "$EVIDENCE_DIR"
