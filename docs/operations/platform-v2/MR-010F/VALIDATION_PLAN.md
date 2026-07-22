# MR-010F Recovery-Time Idempotency Validation Plan

## Scenarios

- same idempotency key and same payload while publisher unavailable;
- same key and conflicting payload while unavailable;
- duplicate publisher invocation after restoration;
- duplicate SQS delivery before and after completion;
- retry of an item in `FAILED_RETRYABLE`;
- authorized replay of a terminal publisher event.

## Expected results

- same key/same payload returns or continues the original logical work;
- same key/different payload returns conflict;
- duplicate delivery cannot create a second result;
- stale processing lease follows current claim rules;
- completed/terminal records are skipped safely;
- correlation and request identities remain traceable across attempts.
