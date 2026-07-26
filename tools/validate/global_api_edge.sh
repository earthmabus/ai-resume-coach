#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'HELP'
Usage: tools/validate/global_api_edge.sh

Read-only validation for the deployed Route 53 latency-routed API edge.

Environment:
  EXPECTED_DOMAIN   Defaults to api.resume.michaelpopovich.com.
HELP
}
case "${1:-}" in -h|--help) show_help; exit 0 ;; esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EXPECTED_DOMAIN="${EXPECTED_DOMAIN:-api.resume.michaelpopovich.com}"

fail() { printf 'FAILED: %s\n' "$*" >&2; exit 1; }
for command in terraform jq dig curl; do command -v "$command" >/dev/null || fail "$command is required"; done

routing="$(terraform -chdir="$ROOT_DIR/infra" output -json global_api_routing)"
endpoints="$(terraform -chdir="$ROOT_DIR/infra" output -json regional_api_endpoints)"

echo "$routing" | jq -e '.enabled == true' >/dev/null || fail "global API routing is not enabled"
echo "$routing" | jq -e '.health_checks_enabled == true' >/dev/null || fail "Route 53 health checks are not enabled"
echo "$routing" | jq -e '.routing_policy == "LATENCY"' >/dev/null || fail "routing policy is not LATENCY"
echo "$routing" | jq -e '.routing_enabled.east == true and .routing_enabled.west == true' >/dev/null || fail "both sites are not published"

actual_domain="$(echo "$routing" | jq -r '.domain_name')"
[[ "$actual_domain" == "$EXPECTED_DOMAIN" ]] || fail "unexpected global API domain: $actual_domain"

for site in east west; do
  endpoint="$(echo "$endpoints" | jq -r --arg site "$site" '.[$site]')"
  body="$(curl --fail-with-body --silent --show-error --max-time 20 "${endpoint%/}/health/ready")" \
    || fail "$site direct readiness endpoint failed"
  echo "$body" | jq -e '.status == "ready" or .status == "ok"' >/dev/null \
    || fail "$site direct readiness response is not ready"
done

dig +short "$actual_domain" | grep -q . || fail "global API domain does not resolve"
curl --fail-with-body --silent --show-error --max-time 20 \
  "https://$actual_domain/health/ready" | jq -e '.status == "ready" or .status == "ok"' >/dev/null \
  || fail "global API readiness endpoint failed"

printf 'PASS: Route 53 latency routing and health checks are active for %s\n' "$actual_domain"
