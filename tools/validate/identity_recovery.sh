#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/tools/lib/multi_site.sh"

require_cmd terraform
require_cmd jq
require_cmd aws

new_evidence_dir "ms019-validate"
terraform -chdir="$INFRA_DIR" output -json > "$EVIDENCE_DIR/terraform-outputs.json"

contract="$(jq -c '.cognito_recovery.value // empty' "$EVIDENCE_DIR/terraform-outputs.json")"
[[ -n "$contract" ]] || { echo "cognito_recovery Terraform output is missing" >&2; exit 1; }

echo "$contract" | jq -e '
  .enabled == true and
  .mode == "WARM_STANDBY_RESET_REQUIRED" and
  .standby.region == "us-west-2" and
  .password_continuity == false and
  .session_continuity == false and
  .automated_failover == false
' >/dev/null

pool_id="$(echo "$contract" | jq -r '.standby.user_pool_id')"
client_id="$(echo "$contract" | jq -r '.standby.client_id')"

aws_args=(--region us-west-2)
if [[ -n "${AWS_PROFILE:-}" ]]; then
  aws_args=(--profile "$AWS_PROFILE" "${aws_args[@]}")
fi

aws "${aws_args[@]}" cognito-idp describe-user-pool \
  --user-pool-id "$pool_id" > "$EVIDENCE_DIR/standby-user-pool.json"
aws "${aws_args[@]}" cognito-idp describe-user-pool-client \
  --user-pool-id "$pool_id" \
  --client-id "$client_id" > "$EVIDENCE_DIR/standby-user-pool-client.json"

jq -e --arg pool "$pool_id" '.UserPool.Id == $pool' \
  "$EVIDENCE_DIR/standby-user-pool.json" >/dev/null
jq -e --arg client "$client_id" '.UserPoolClient.ClientId == $client' \
  "$EVIDENCE_DIR/standby-user-pool-client.json" >/dev/null

record "PASSED: MS-019 warm-standby Cognito recovery resources validated"
record "NOTICE: password/session continuity and automatic failover remain intentionally false"
printf 'Evidence: %s\n' "$EVIDENCE_DIR"
