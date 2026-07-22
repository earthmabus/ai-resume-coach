#!/usr/bin/env bash

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

  local response challenge new_auth_token jwt_parts

  response="$(
    aws cognito-idp initiate-auth \
      --region us-east-1 \
      --client-id 6vhud9ve4t9acijtugqaf338mp \
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
