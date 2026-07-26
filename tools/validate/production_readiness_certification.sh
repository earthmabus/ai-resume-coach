#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/tools/lib/multi_site.sh"

require_cmd terraform
require_cmd jq
require_cmd aws
require_cmd curl
require_cmd python

profile="${CERTIFICATION_PROFILE:-pre-production}"
profile="${profile,,}"
profile="${profile//_/-}"
case "$profile" in
  development|integration|pre-production|production) ;;
  *) echo "Invalid certification profile: $profile" >&2; exit 2 ;;
esac

new_evidence_dir "ms024a-assess-${profile}"
CHECKS_FILE="$EVIDENCE_DIR/checks.jsonl"
: > "$CHECKS_FILE"

add_check() {
  local name="$1" category="$2" status="$3" detail="$4" evidence="${5:-}"
  jq -cn --arg name "$name" --arg category "$category" --arg status "$status" --arg detail "$detail" --arg evidence "$evidence" \
    '{name:$name,category:$category,status:$status,detail:$detail,evidence:(if $evidence == "" then null else $evidence end)}' >> "$CHECKS_FILE"
}
pass() { add_check "$1" "$2" PASS "$3" "${4:-}"; }
warn() { add_check "$1" "$2" WARN "$3" "${4:-}"; }
fail() { add_check "$1" "$2" FAIL "$3" "${4:-}"; }

terraform -chdir="$INFRA_DIR" output -json > "$EVIDENCE_DIR/terraform-outputs.json"
outputs="$EVIDENCE_DIR/terraform-outputs.json"
deployment_id="$(jq -r '.regional_sites.value.east.deploymentId // empty' "$outputs")"
[[ -n "$deployment_id" ]] || { echo "Unable to resolve deployment ID" >&2; exit 2; }

if jq -e '.regional_sites.value.east.region == "us-east-1" and .regional_sites.value.west.region == "us-west-2"' "$outputs" >/dev/null; then
  pass active_active_topology Architecture "Both approved active application sites are deployed." terraform-outputs.json
else
  fail active_active_topology Architecture "The approved us-east-1/us-west-2 active-active topology is incomplete." terraform-outputs.json
fi

if jq -e '.global_api_routing.value.enabled == true and .global_api_routing.value.health_checks_enabled == true' "$outputs" >/dev/null; then
  pass global_routing Reliability "Latency routing and Route 53 health checks are enabled." terraform-outputs.json
else
  fail global_routing Reliability "Global latency routing and health checks must both be enabled." terraform-outputs.json
fi

if jq -e '.resume_analysis_data.value.consistency_mode == "STRONG" and (.resume_analysis_data.value.replica_regions | sort) == ["us-east-1","us-west-2"] and .resume_analysis_data.value.witness_region == "us-east-2"' "$outputs" >/dev/null; then
  pass mrsc_data Reliability "DynamoDB MRSC matches the approved replicas and witness." terraform-outputs.json
else
  fail mrsc_data Reliability "DynamoDB MRSC does not match the approved topology." terraform-outputs.json
fi

if jq -e '.document_replication.value.enabled == true and .document_replication.value.mode == "BIDIRECTIONAL_CRR"' "$outputs" >/dev/null; then
  pass document_continuity Reliability "Bidirectional document replication is enabled." terraform-outputs.json
else
  fail document_continuity Reliability "Bidirectional document replication is not enabled." terraform-outputs.json
fi

if jq -e '.processing_ownership.value.mode == "PERSISTED_OWNER_REGION" and .processing_ownership.value.worker_enforcement == "FAIL_CLOSED" and .processing_ownership.value.automatic_reassignment == false' "$outputs" >/dev/null; then
  pass processing_ownership Reliability "Persisted owner-region enforcement is fail-closed." terraform-outputs.json
else
  fail processing_ownership Reliability "Processing ownership does not match the approved fail-closed contract." terraform-outputs.json
fi

if jq -e '.cognito_recovery.value.enabled == true and .cognito_recovery.value.mode == "WARM_STANDBY_RESET_REQUIRED" and .cognito_recovery.value.automated_failover == false' "$outputs" >/dev/null; then
  pass identity_recovery Reliability "Warm-standby identity recovery is enabled with truthful reset-required boundaries." terraform-outputs.json
else
  fail identity_recovery Reliability "The approved warm-standby identity recovery contract is not enabled." terraform-outputs.json
fi

for site in east west; do
  endpoint="$(jq -r --arg site "$site" '.regional_api_endpoints.value[$site]' "$outputs")"
  if curl --fail-with-body --silent --show-error --max-time 20 "$endpoint/health/ready" > "$EVIDENCE_DIR/${site}-ready.json"; then
    pass "${site}_readiness" Reliability "The $site regional readiness endpoint passed." "${site}-ready.json"
  else
    fail "${site}_readiness" Reliability "The $site regional readiness endpoint failed." "${site}-ready.json"
  fi
done

global_endpoint="https://$(jq -r '.global_api_routing.value.domain_name' "$outputs")"
if curl --fail-with-body --silent --show-error --max-time 20 "$global_endpoint/health/ready" > "$EVIDENCE_DIR/global-ready.json"; then
  pass global_readiness Reliability "The global readiness endpoint passed." global-ready.json
else
  fail global_readiness Reliability "The global readiness endpoint failed." global-ready.json
fi

if jq -e '.production_observability.value.enabled == true and .production_observability.value.dashboard_enabled == true and .production_observability.value.operational_alarms == true and .production_observability.value.synthetic_monitoring == true' "$outputs" >/dev/null; then
  pass observability_contract Operations "Dashboard, regional alarms, and synthetic monitoring are enabled." terraform-outputs.json
else
  fail observability_contract Operations "The production observability contract is incomplete." terraform-outputs.json
fi

mapfile -t ALARM_NAMES < <(jq -r '.observability.value.alarms.names[]' "$outputs")
mapfile -t EAST_ALARMS < <(printf '%s\n' "${ALARM_NAMES[@]:-}" | grep -- '-use1-' || true)
mapfile -t WEST_ALARMS < <(printf '%s\n' "${ALARM_NAMES[@]:-}" | grep -- '-usw2-' || true)
aws_cli --region us-east-1 cloudwatch describe-alarms --alarm-names "${EAST_ALARMS[@]}" > "$EVIDENCE_DIR/east-alarms.json"
aws_cli --region us-west-2 cloudwatch describe-alarms --alarm-names "${WEST_ALARMS[@]}" > "$EVIDENCE_DIR/west-alarms.json"
east_count="$(jq '.MetricAlarms | length' "$EVIDENCE_DIR/east-alarms.json")"
west_count="$(jq '.MetricAlarms | length' "$EVIDENCE_DIR/west-alarms.json")"
if [[ "$east_count" -eq "${#EAST_ALARMS[@]}" && "$west_count" -eq "${#WEST_ALARMS[@]}" && $((east_count + west_count)) -eq "${#ALARM_NAMES[@]}" ]]; then
  pass regional_alarms Operations "All ${#ALARM_NAMES[@]} curated alarms exist (${#EAST_ALARMS[@]} east, ${#WEST_ALARMS[@]} west)." east-alarms.json,west-alarms.json
else
  fail regional_alarms Operations "The curated regional alarm inventory is incomplete." east-alarms.json,west-alarms.json
fi

if jq -e '.production_observability.value.notification_actions_set == true' "$outputs" >/dev/null; then
  pass alarm_notifications Operations "Alarm notification actions are configured." terraform-outputs.json
elif [[ "$profile" == "production" ]]; then
  fail alarm_notifications Operations "Alarm notification actions are required by the production profile but are not configured." terraform-outputs.json
elif [[ "$profile" == "development" ]]; then
  pass alarm_notifications Operations "Alarm notification actions are optional for the development profile and are not configured." terraform-outputs.json
else
  warn alarm_notifications Operations "Alarm notification actions are not configured; this is accepted by the $profile profile." terraform-outputs.json
fi

validate_canary() {
  local site="$1" region="$2" name="$3" file="$EVIDENCE_DIR/${site}-canary.json"
  if aws_cli --region "$region" synthetics get-canary --name "$name" > "$file" \
      && jq -e '.Canary.Status.State == "RUNNING" or .Canary.Status.State == "READY"' "$file" >/dev/null; then
    pass "${site}_canary" Operations "$name is running." "${site}-canary.json"
  else
    fail "${site}_canary" Operations "$name is not running." "${site}-canary.json"
  fi
}
validate_canary global us-east-1 "$(jq -r '.observability.value.synthetics.canaries.global' "$outputs")"
validate_canary east us-east-1 "$(jq -r '.observability.value.synthetics.canaries.east' "$outputs")"
validate_canary west us-west-2 "$(jq -r '.observability.value.synthetics.canaries.west' "$outputs")"

if jq -e '.observability.value.telemetry.structured_logging_enabled == true and .observability.value.telemetry.privacy.authorization_header_redacted == true' "$outputs" >/dev/null; then
  pass structured_logging Security "Structured logging and authorization-header redaction are enabled." terraform-outputs.json
else
  fail structured_logging Security "Structured logging or required privacy redaction is disabled." terraform-outputs.json
fi

if jq -e '.document_replication.value.encryption == "SSE_S3_AES256" and .resume_analysis_data.value.pitr_enabled == true' "$outputs" >/dev/null; then
  pass data_protection Security "Document encryption and DynamoDB point-in-time recovery are enabled." terraform-outputs.json
else
  fail data_protection Security "Required encryption or point-in-time recovery is missing." terraform-outputs.json
fi

if jq -e '.edge_security.value.cognito_waf.enabled == true' "$outputs" >/dev/null; then
  pass cognito_waf Security "Cognito WAF protection is enabled." terraform-outputs.json
elif [[ "$profile" == "production" ]]; then
  fail cognito_waf Security "Cognito WAF is required by the production profile but is not enabled." terraform-outputs.json
elif [[ "$profile" == "development" ]]; then
  pass cognito_waf Security "Cognito WAF is optional for the development profile and is not enabled." terraform-outputs.json
else
  warn cognito_waf Security "Cognito WAF is recommended but not required by the $profile profile." terraform-outputs.json
fi

if jq -e '.operations.value.production_readiness_enforced == true' "$outputs" >/dev/null; then
  pass readiness_enforcement Governance "Terraform production-readiness enforcement is enabled." terraform-outputs.json
elif [[ "$profile" == "production" ]]; then
  fail readiness_enforcement Governance "Terraform production-readiness enforcement is required by the production profile but is not enabled." terraform-outputs.json
elif [[ "$profile" == "development" ]]; then
  pass readiness_enforcement Governance "Terraform production-readiness enforcement is optional for the development profile and is disabled." terraform-outputs.json
else
  warn readiness_enforcement Governance "Terraform production-readiness enforcement is disabled; this is accepted by the $profile profile." terraform-outputs.json
fi

if jq -e '.operations.value.production_ready == true and (.operations.value.missing_production_controls | length) == 0' "$outputs" >/dev/null; then
  pass terraform_readiness_gate Governance "Terraform reports no missing production controls." terraform-outputs.json
else
  missing="$(jq -r '.operations.value.missing_production_controls | join(", ")' "$outputs")"
  if [[ "$profile" == "production" ]]; then
    fail terraform_readiness_gate Governance "Terraform reports missing production controls: ${missing:-unknown}." terraform-outputs.json
  elif [[ "$profile" == "development" ]]; then
    pass terraform_readiness_gate Governance "Terraform production controls are not complete (${missing:-unknown}); they are not required by the development profile." terraform-outputs.json
  else
    warn terraform_readiness_gate Governance "Terraform production controls are not complete (${missing:-unknown}); this is accepted by the $profile profile." terraform-outputs.json
  fi
fi

if [[ -f "$ROOT_DIR/docs/certification/MR-014_MULTI_SITE_CERTIFICATION.md" ]]; then
  pass resilience_certification Governance "The durable MR-014 multi-site certification record exists." ../../docs/certification/MR-014_MULTI_SITE_CERTIFICATION.md
else
  fail resilience_certification Governance "The durable MR-014 multi-site certification record is missing."
fi

set +e
python "$ROOT_DIR/tools/resilience/production_readiness_certification.py" \
  --checks "$CHECKS_FILE" \
  --deployment-id "$deployment_id" \
  --profile "$profile" \
  --report "$EVIDENCE_DIR/report.json" \
  --certification "$EVIDENCE_DIR/MS-024A_PROFILE_READINESS_CERTIFICATION.md" \
  | tee "$EVIDENCE_DIR/report.txt"
status=$?
set -e
printf 'Evidence: %s\n' "$EVIDENCE_DIR"
exit "$status"
