#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INFRA_DIR="$ROOT_DIR/infra"
EVIDENCE_ROOT="${EVIDENCE_ROOT:-$ROOT_DIR/evidence}"
AWS_PROFILE_ARG=()
[[ -n "${AWS_PROFILE:-}" ]] && AWS_PROFILE_ARG=(--profile "$AWS_PROFILE")

require_cmd() {
  command -v "$1" >/dev/null || {
    echo "Missing command: $1" >&2
    exit 2
  }
}

require_env() {
  [[ -n "${!1:-}" ]] || {
    echo "Missing environment variable: $1" >&2
    exit 2
  }
}

aws_cli() {
  aws "${AWS_PROFILE_ARG[@]}" "$@"
}

new_evidence_dir() {
  local prefix="$1"
  local stamp
  if [[ -n "${EVIDENCE_DIR_OVERRIDE:-}" ]]; then
    EVIDENCE_DIR="$EVIDENCE_DIR_OVERRIDE"
    unset EVIDENCE_DIR_OVERRIDE
  else
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    EVIDENCE_DIR="$EVIDENCE_ROOT/${prefix}-${stamp}"
  fi
  mkdir -p "$EVIDENCE_DIR"
  export EVIDENCE_DIR
}

record() {
  printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*" |
    tee -a "$EVIDENCE_DIR/execution.log"
}

confirm_mutation() {
  [[ "${CONFIRM_MUTATION:-NO}" == "YES" ]] || {
    echo "Mutation blocked. Set CONFIRM_MUTATION=YES after authorization." >&2
    exit 3
  }
}

terraform_output_json() {
  terraform -chdir="$INFRA_DIR" output -json
}

regional_endpoints() {
  terraform_output_json > "$EVIDENCE_DIR/terraform-outputs.json"
  EAST_API="$(python -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["regional_api_endpoints"]["value"]["east"])' "$EVIDENCE_DIR/terraform-outputs.json")"
  WEST_API="$(python -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["regional_api_endpoints"]["value"]["west"])' "$EVIDENCE_DIR/terraform-outputs.json")"
  export EAST_API WEST_API
}

# Resolve Terraform variables that must remain aligned with the already-deployed
# runtime during routing-only certification. Ambient TF_VAR_* values are not
# authoritative for certification because they often reflect local development.
prepare_deployed_runtime_alignment() {
  local output_file="${1:-$EVIDENCE_DIR/deployed-runtime-alignment.json}"
  local outputs_file="${2:-$EVIDENCE_DIR/terraform-outputs.json}"

  [[ -f "$outputs_file" ]] || terraform_output_json > "$outputs_file"

  local east_api west_api registration
  east_api="$(jq -r '.regional_foundations.value.east.compute.api.name // empty' "$outputs_file")"
  west_api="$(jq -r '.regional_foundations.value.west.compute.api.name // empty' "$outputs_file")"
  registration="$(jq -r '.registration_notification_lambda_name.value // empty' "$outputs_file")"
  [[ -n "$east_api" && -n "$west_api" && -n "$registration" ]] || {
    echo "Unable to resolve deployed Lambda names from Terraform outputs" >&2
    return 9
  }

  local east_file="$EVIDENCE_DIR/east-api-runtime.json"
  local west_file="$EVIDENCE_DIR/west-api-runtime.json"
  local registration_file="$EVIDENCE_DIR/registration-runtime.json"
  aws_cli lambda get-function-configuration --region "${EAST_REGION:-us-east-1}" --function-name "$east_api" > "$east_file"
  aws_cli lambda get-function-configuration --region "${WEST_REGION:-us-west-2}" --function-name "$west_api" > "$west_file"
  aws_cli lambda get-function-configuration --region "${EAST_REGION:-us-east-1}" --function-name "$registration" > "$registration_file"

  local east_deployment west_deployment registration_deployment east_provider west_provider
  east_deployment="$(jq -r '.Environment.Variables.DEPLOYMENT_ID // empty' "$east_file")"
  west_deployment="$(jq -r '.Environment.Variables.DEPLOYMENT_ID // empty' "$west_file")"
  registration_deployment="$(jq -r '.Environment.Variables.DEPLOYMENT_ID // empty' "$registration_file")"
  east_provider="$(jq -r '.Environment.Variables.ANALYSIS_PROVIDER // empty' "$east_file")"
  west_provider="$(jq -r '.Environment.Variables.ANALYSIS_PROVIDER // empty' "$west_file")"

  [[ -n "$east_deployment" && "$east_deployment" == "$west_deployment" && "$east_deployment" == "$registration_deployment" ]] || {
    echo "Deployed DEPLOYMENT_ID values are missing or inconsistent across Lambda functions" >&2
    return 9
  }
  [[ -n "$east_provider" && "$east_provider" == "$west_provider" ]] || {
    echo "Deployed ANALYSIS_PROVIDER values are missing or inconsistent across regional APIs" >&2
    return 9
  }

  jq -n \
    --arg deploymentId "$east_deployment" \
    --arg analysisProvider "$east_provider" \
    --arg eastApi "$east_api" \
    --arg westApi "$west_api" \
    --arg registration "$registration" \
    '{deploymentId:$deploymentId,analysisProvider:$analysisProvider,functions:{eastApi:$eastApi,westApi:$westApi,registrationNotification:$registration},ambientOverrides:{deploymentId:(env.TF_VAR_deployment_id // null),analysisProvider:(env.TF_VAR_analysis_provider // null)}}' \
    > "$output_file"

  TERRAFORM_RUNTIME_ALIGNMENT_ARGS=(
    -var="deployment_id=$east_deployment"
    -var="analysis_provider=$east_provider"
  )
}

health_capture() {
  local name="$1"
  local endpoint="$2"
  curl --fail-with-body --silent --show-error --max-time 15 \
    "$endpoint/health/live" > "$EVIDENCE_DIR/${name}-live.json"
  curl --fail-with-body --silent --show-error --max-time 20 \
    "$endpoint/health/ready" > "$EVIDENCE_DIR/${name}-ready.json"
}
