#!/usr/bin/env bash

show_help() {
  cat <<'EOF'
Usage: tools/prepare/auth.sh [COMMAND] [OPTIONS]

Purpose:
  Acquire a Cognito ID token and export AUTH_TOKEN.

Environment variables:
  SYNTHETIC_USERNAME
      Set explicitly for the target environment.

  SYNTHETIC_PASSWORD
      Set explicitly for the target environment.

  COGNITO_USER_POOL_CLIENT_ID
      Optional override. When omitted, read cognito_user_pool_client_id from
      Terraform output in TERRAFORM_DIR.

  TERRAFORM_DIR
      Optional Terraform root directory (default: <repository>/infra).

  AWS_PROFILE
      Optional. List values with: aws configure list-profiles

Safety:
  --help performs no validation, file creation, AWS calls, or mutations.
EOF
}

case "${1:-}" in -h|--help) show_help; exit 0 ;; esac

acquire_auth_token() {
  if [[ -z "${SYNTHETIC_USERNAME:-}" ]]; then
    echo "SYNTHETIC_USERNAME is required" >&2
    return 1
  fi

  if [[ -z "${SYNTHETIC_PASSWORD:-}" ]]; then
    echo "SYNTHETIC_PASSWORD is required" >&2
    return 1
  fi

  unset AUTH_TOKEN

  local response challenge new_auth_token jwt_parts client_id terraform_dir root_dir

  root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  terraform_dir="${TERRAFORM_DIR:-$root_dir/infra}"
  client_id="${COGNITO_USER_POOL_CLIENT_ID:-}"

  if [[ -z "$client_id" ]]; then
    command -v terraform >/dev/null 2>&1 || {
      echo "terraform is required when COGNITO_USER_POOL_CLIENT_ID is not set" >&2
      return 1
    }
    client_id="$(terraform -chdir="$terraform_dir" output -raw cognito_user_pool_client_id)" || {
      echo "Unable to read cognito_user_pool_client_id from Terraform outputs" >&2
      return 1
    }
  fi

  response="$(
    aws cognito-idp initiate-auth \
      --region us-east-1 \
      --client-id "$client_id" \
      --auth-flow USER_PASSWORD_AUTH \
      --auth-parameters \
        "USERNAME=${SYNTHETIC_USERNAME},PASSWORD=${SYNTHETIC_PASSWORD}" \
      --output json
  )" || {
    echo "Cognito authentication command failed" >&2
    return 1
  }

  challenge="$(jq -r '.ChallengeName // empty' <<<"$response")"

  if [[ -n "$challenge" ]]; then
    echo "Cognito authentication requires challenge: $challenge" >&2
    return 1
  fi

  new_auth_token="$(
    jq -r '.AuthenticationResult.IdToken // empty' <<<"$response"
  )"

  if [[ -z "$new_auth_token" || "$new_auth_token" == "None" ]]; then
    echo "Cognito did not return an ID token" >&2
    return 1
  fi

  jwt_parts="$(awk -F. '{print NF}' <<<"$new_auth_token")"

  if [[ "$jwt_parts" -ne 3 ]]; then
    echo "Cognito returned a value that is not a three-part JWT" >&2
    return 1
  fi

  export AUTH_TOKEN="$new_auth_token"
  echo "AUTH_TOKEN acquired successfully"
}

acquire_auth_token
