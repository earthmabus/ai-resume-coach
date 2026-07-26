# MS-023 — Production Observability

## Decision

MS-023 activates the observability capabilities that already existed behind
feature flags and closes two remaining gaps: a global health canary and Lambda
throttling alarms. The deployed contract contains one shared CloudWatch
operations dashboard, a curated regional alarm set, and three CloudWatch
Synthetics canaries for the global, east, and west public API endpoints.

## Operator workflow

```bash
./tools/resilience/activate_production_observability.sh plan

CONFIRM_MUTATION=YES \
  ./tools/resilience/activate_production_observability.sh apply

./tools/resilience/activate_production_observability.sh validate
```

The plan preserves global API routing, warm-standby Cognito recovery, document
replication, and deployed Lambda runtime alignment.

## Monitoring contract

The dashboard covers regional API volume, 4XX/5XX responses, latency, Lambda
activity, duration, errors, throttles, queue depth and age, asynchronous
throughput, DLQ depth, DynamoDB capacity and throttles, custom worker/outbox
failure metrics, synthetic success, and recent regional error logs.

Regional alarms cover:

- API 5XX and p95 latency;
- API, worker, and outbox Lambda errors and throttles;
- processing queue age and depth;
- processing DLQ messages;
- DynamoDB throttles;
- worker-record and outbox-publish failures.

The canaries call `/health`, `/health/live`, and `/health/ready`. Each canary does not authenticate, upload resumes, change processing ownership, or mutate application
data.

## Notification boundary

Alarm state is useful even when no action is configured. To route alarm and
recovery notifications, supply a JSON list of action ARNs during planning:

```bash
export OBSERVABILITY_ALARM_ACTIONS='["arn:aws:sns:us-east-1:123456789012:platform-alerts"]'
```

An empty list is allowed and is surfaced as a validation warning rather than a
false claim that operators will receive notifications.

## Cost boundary

Enabling MS-023 creates CloudWatch alarms, one dashboard, S3 artifact storage,
IAM roles, and three scheduled Synthetics canaries. These resources incur
ongoing AWS charges. The default five-minute canary schedule and seven-day
artifact retention are deliberately cost-conscious, but operators must review
actual regional pricing and usage.

AWS X-Ray active tracing remains independently controlled and is not required
by this slice.
