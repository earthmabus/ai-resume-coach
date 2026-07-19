# Incident Evidence Collection Runbook

Use `tools/multi_site/collect_evidence.sh` for a read-only snapshot.

Collect UTC timestamps, approved AWS identity, Terraform outputs and no-drift
result, regional health, Lambda mappings, queue and DLQ attributes, alarms,
bounded recent logs, DynamoDB table/index/replica status, deployment IDs, and
routing state.

Never retain tokens, secrets, resume text, job descriptions, prompts, provider
responses, full queue URLs, raw environment variables, or full DynamoDB items.
