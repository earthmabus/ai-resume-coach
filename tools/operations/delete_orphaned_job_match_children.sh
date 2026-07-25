#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'HELP'
Usage: tools/operations/delete_orphaned_job_match_children.sh [OPTIONS]

Safely inspect or delete orphaned Resume Tailoring and Interview Preparation
records for a Job Match whose parent record has already been removed.

Required:
  --user-id ID       Cognito user subject that owns the records
  --match-id ID      Job Match identifier

Options:
  --table-name NAME  DynamoDB table name. Overrides discovery.
  --region REGION    AWS region used for DynamoDB calls (default: us-east-1)
  --profile PROFILE  AWS CLI profile used for discovery and DynamoDB calls
  --execute          Perform deletion. Without this flag, run as a dry-run.
  -h, --help         Show this help.

Table discovery order:
  1. --table-name
  2. TABLE_NAME environment variable
  3. Terraform resume_analysis_data.table_name output
  4. Legacy Terraform resume_analysis_table_name output
  5. A unique AWS table containing "resume-analysis"

Examples:
  tools/operations/delete_orphaned_job_match_children.sh \
    --user-id e44884e8-2081-709f-a162-44a7fa12753a \
    --match-id 7bf775fe-f809-4ad1-a194-0ab42780d707

  tools/operations/delete_orphaned_job_match_children.sh \
    --table-name ai-resume-coach-dev-resume-analysis \
    --region us-east-1 \
    --profile default \
    --user-id e44884e8-2081-709f-a162-44a7fa12753a \
    --match-id 7bf775fe-f809-4ad1-a194-0ab42780d707 \
    --execute
HELP
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REGION="us-east-1"
TABLE_NAME="${TABLE_NAME:-}"
AWS_PROFILE_NAME=""
USER_ID=""
MATCH_ID=""
EXECUTE=false

require_option_value() {
  local option="$1"
  local value="${2:-}"
  if [[ -z "$value" || "$value" == --* ]]; then
    echo "$option requires a value" >&2
    exit 2
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user-id)
      require_option_value "$1" "${2:-}"
      USER_ID="$2"
      shift 2
      ;;
    --match-id)
      require_option_value "$1" "${2:-}"
      MATCH_ID="$2"
      shift 2
      ;;
    --table-name)
      require_option_value "$1" "${2:-}"
      TABLE_NAME="$2"
      shift 2
      ;;
    --region)
      require_option_value "$1" "${2:-}"
      REGION="$2"
      shift 2
      ;;
    --profile)
      require_option_value "$1" "${2:-}"
      AWS_PROFILE_NAME="$2"
      shift 2
      ;;
    --execute)
      EXECUTE=true
      shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      show_help >&2
      exit 2
      ;;
  esac
done

for command in aws jq; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Required command not found: $command" >&2
    exit 1
  }
done

[[ -n "$USER_ID" ]] || { echo "--user-id is required" >&2; exit 2; }
[[ -n "$MATCH_ID" ]] || { echo "--match-id is required" >&2; exit 2; }

AWS_ARGS=(--region "$REGION")
if [[ -n "$AWS_PROFILE_NAME" ]]; then
  AWS_ARGS+=(--profile "$AWS_PROFILE_NAME")
fi

terraform_output_raw() {
  local output_name="$1"
  command -v terraform >/dev/null 2>&1 || return 1
  terraform -chdir="$ROOT_DIR/infra" output -raw "$output_name" 2>/dev/null
}

terraform_output_json() {
  local output_name="$1"
  command -v terraform >/dev/null 2>&1 || return 1
  terraform -chdir="$ROOT_DIR/infra" output -json "$output_name" 2>/dev/null
}

discover_table_name() {
  local discovered=""
  local output_json=""

  output_json="$(terraform_output_json resume_analysis_data || true)"
  if [[ -n "$output_json" ]]; then
    discovered="$(jq -r '.table_name // empty' <<<"$output_json")"
    if [[ -n "$discovered" ]]; then
      printf '%s\n' "$discovered"
      return 0
    fi
  fi

  discovered="$(terraform_output_raw resume_analysis_table_name || true)"
  if [[ -n "$discovered" ]]; then
    printf '%s\n' "$discovered"
    return 0
  fi

  local tables_json candidates count
  tables_json="$(aws dynamodb list-tables "${AWS_ARGS[@]}" --output json)"
  candidates="$(jq -c '[.TableNames[] | select(contains("resume-analysis"))]' <<<"$tables_json")"
  count="$(jq 'length' <<<"$candidates")"

  if [[ "$count" -eq 1 ]]; then
    jq -r '.[0]' <<<"$candidates"
    return 0
  fi

  if [[ "$count" -eq 0 ]]; then
    echo "Unable to discover a DynamoDB table containing 'resume-analysis'. Supply --table-name." >&2
  else
    echo "Multiple DynamoDB tables contain 'resume-analysis'. Supply --table-name explicitly:" >&2
    jq -r '.[] | "  - \(.)"' <<<"$candidates" >&2
  fi
  return 1
}

if [[ -z "$TABLE_NAME" ]]; then
  TABLE_NAME="$(discover_table_name)"
fi

PARENT_KEY="$(jq -cn --arg pk "USER#$USER_ID" --arg sk "MATCH#$MATCH_ID" '{pk:{S:$pk},sk:{S:$sk}}')"
PARENT="$(aws dynamodb get-item "${AWS_ARGS[@]}" --table-name "$TABLE_NAME" --key "$PARENT_KEY" --consistent-read --output json)"

if [[ "$(jq '.Item | length // 0' <<<"$PARENT")" -gt 0 ]]; then
  echo "Refusing cleanup: the parent Job Match still exists." >&2
  exit 1
fi

CHILDREN="$(aws dynamodb query \
  "${AWS_ARGS[@]}" \
  --table-name "$TABLE_NAME" \
  --key-condition-expression 'pk = :pk' \
  --expression-attribute-values "$(jq -cn --arg pk "MATCH#$MATCH_ID" '{":pk":{S:$pk}}')" \
  --consistent-read \
  --output json)"

MATCHING="$(jq -c --arg user "$USER_ID" --arg match "$MATCH_ID" '[.Items[] | select((.userId.S // "") == $user and (.matchId.S // "") == $match)]' <<<"$CHILDREN")"
COUNT="$(jq 'length' <<<"$MATCHING")"

echo "Table: $TABLE_NAME"
echo "Region: $REGION"
if [[ -n "$AWS_PROFILE_NAME" ]]; then
  echo "Profile: $AWS_PROFILE_NAME"
fi
echo "Orphaned child records found: $COUNT"
jq '[.[] | {pk:.pk.S, sk:.sk.S, recordType:(.recordType.S // ""), status:(.status.S // "")}]' <<<"$MATCHING"

if [[ "$EXECUTE" != true ]]; then
  echo "Dry-run only. Re-run with --execute to delete these records."
  exit 0
fi

if [[ "$COUNT" -eq 0 ]]; then
  echo "No orphaned child records require deletion."
  exit 0
fi

while IFS= read -r child; do
  key="$(jq -c '{pk:.pk, sk:.sk}' <<<"$child")"
  aws dynamodb delete-item \
    "${AWS_ARGS[@]}" \
    --table-name "$TABLE_NAME" \
    --key "$key" \
    --condition-expression 'userId = :userId AND matchId = :matchId' \
    --expression-attribute-values "$(jq -cn --arg user "$USER_ID" --arg match "$MATCH_ID" '{":userId":{S:$user},":matchId":{S:$match}}')"
done < <(jq -c '.[]' <<<"$MATCHING")

echo "Deleted $COUNT orphaned child record(s)."
