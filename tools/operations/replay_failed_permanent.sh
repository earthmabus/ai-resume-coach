#!/usr/bin/env bash
set -euo pipefail
cat <<'HELP'
Replay a FAILED_PERMANENT outbox event using the canonical replay tool.

Example:
  python tools/operations/replay_outbox.py \
    --event-id EVENT_ID \
    --table-name ai-resume-coach-dev-resume-analysis \
    --region us-east-1 \
    --operator "$USER"

The replay operation uses a conditional DynamoDB update, resets delivery
attempts, restores pending-index fields, removes permanent-failure metadata,
and records replay audit fields. It does not send directly to SQS.
HELP
