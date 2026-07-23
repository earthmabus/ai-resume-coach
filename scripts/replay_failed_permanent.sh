# Replay:
# - only accepts FAILED_PERMANENT
# - uses a conditional DynamoDB update
# - resets deliveryAttempts to zero
# - restores the pending GSI fields
# - removes permanent-failure metadata
# - records replayCount, replayedAt, and replayedBy
# - does not send directly to SQS

python tools/operations/replay_outbox.py \
  --event-id EVENT_ID \
  --table-name ai-resume-coach-dev-resume-analysis \
  --region us-east-1 \
  --operator "$USER"
