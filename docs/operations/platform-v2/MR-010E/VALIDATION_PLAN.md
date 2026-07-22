# MR-010E Retry and DLQ Validation Plan

## Cases

1. Retryable worker failure below max attempts.
2. Retryable worker failure at exhaustion.
3. Permanent worker failure.
4. Mixed SQS batch containing one failing and one healthy record.
5. Publisher retryable delivery failure.
6. Publisher permanent failure and authorized replay path.

## Assertions

- retry classification matches `retry_policy.py`;
- attempt counters increase monotonically;
- backoff timestamps are bounded and present;
- partial batch response retries only failed records;
- healthy records complete;
- terminal business status matches terminal envelope;
- processing DLQ and terminal-failure DLQ roles remain distinct;
- replay requires explicit authorization and preserves idempotency.
