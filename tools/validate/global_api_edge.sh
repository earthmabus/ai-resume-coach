#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'EOF'
Usage: tools/validate/global_api_edge.sh [COMMAND] [OPTIONS]

Purpose:
  Validate the deployed global API DNS and readiness endpoint.

Environment variables:
  TFVARS_FILE
      Path to a complete tfvars profile. Compose with: tools/prepare/certification_profile.sh compose

  EXPECTED_DOMAIN
      Set explicitly for the target environment.

Safety:
  --help performs no validation, file creation, AWS calls, or mutations.
EOF
}

case "${1:-}" in -h|--help) show_help; exit 0 ;; esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TFVARS_FILE="${TFVARS_FILE:-$ROOT_DIR/infra/global-api-routing.generated.tfvars}"
EXPECTED_DOMAIN="${EXPECTED_DOMAIN:-api.resume.michaelpopovich.com}"

fail() {
  printf 'FAILED: %s\n' "$*" >&2
  exit 1
}

[[ -f "$TFVARS_FILE" ]] || fail "tfvars file not found: $TFVARS_FILE"

output="$(terraform -chdir="$ROOT_DIR/infra" output -json global_api_routing)"

echo "$output" | jq -e '.enabled == true' >/dev/null \
  || fail "global API routing is not enabled in Terraform state"
echo "$output" | jq -e '.certificate_management == "EXTERNAL"' >/dev/null \
  || fail "certificate management mode is missing"
echo "$output" | jq -e '.routing_enabled.east == true and .routing_enabled.west == true' >/dev/null \
  || fail "both active sites are not published"

actual_domain="$(echo "$output" | jq -r '.domain_name')"
[[ "$actual_domain" == "$EXPECTED_DOMAIN" ]] \
  || fail "unexpected global API domain: $actual_domain"

command -v dig >/dev/null || fail "dig is required"
command -v curl >/dev/null || fail "curl is required"

dig +short "$actual_domain" | grep -q . \
  || fail "global API domain does not resolve"

curl --fail-with-body --silent --show-error --max-time 20 \
  "https://$actual_domain/health/ready" | jq -e '.status == "ready" or .status == "ok"' >/dev/null \
  || fail "global API readiness endpoint failed"

printf 'Global API edge validation passed: https://%s\n' "$actual_domain"
