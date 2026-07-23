#!/usr/bin/env bash
# Shared environment-contract helpers. Source this file; do not execute it.

_env_is_sensitive() {
  [[ "$1" =~ (TOKEN|PASSWORD|SECRET|PRIVATE_KEY|API_KEY|CREDENTIAL) ]]
}

env_value_display() {
  local name="$1" value="${!1-}"
  if [[ -z "${!1+x}" ]]; then printf 'UNSET'; return; fi
  if [[ -z "$value" ]]; then printf 'SET BUT EMPTY'; return; fi
  if _env_is_sensitive "$name"; then printf '[SET, REDACTED, %s characters]' "${#value}"; else printf '%s' "$value"; fi
}

print_environment_contract() {
  local heading="$1"; shift
  printf '%s\n' "$heading"
  printf '%*s\n' "${#heading}" '' | tr ' ' '-'
  local name
  for name in "$@"; do printf '%-42s %s\n' "$name" "$(env_value_display "$name")"; done
}

require_environment() {
  local missing=() name
  for name in "$@"; do [[ -n "${!name:-}" ]] || missing+=("$name"); done
  ((${#missing[@]}==0)) && return 0
  printf 'ENVIRONMENT PREFLIGHT FAILED\n\nRequired variables missing or empty:\n' >&2
  printf '  - %s\n' "${missing[@]}" >&2
  return 2
}

require_file_env() {
  local name="$1" value="${!1:-}"
  [[ -n "$value" ]] || { echo "Missing environment variable: $name" >&2; return 2; }
  [[ -f "$value" ]] || { echo "$name does not reference a file: $value" >&2; return 2; }
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  cat <<'EOF'
Usage: source tools/lib/environment.sh

Purpose:
  Shared functions for declaring, displaying, redacting, and validating script
  environment contracts. This file is intended to be sourced by other tools.

Functions:
  env_value_display NAME       Display a value or a safe redacted status.
  print_environment_contract HEADING NAME...
                               Print environment names and current values.
  require_environment NAME... Fail when any required value is unset or empty.
  require_file_env NAME        Require NAME to point to an existing file.
EOF
fi
