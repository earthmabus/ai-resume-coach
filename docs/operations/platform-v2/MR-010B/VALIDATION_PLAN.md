# MR-010B Outbox Publisher Recovery Validation Plan

## Failure boundary

Interrupt dispatch after durable business/outbox creation and before regional SQS delivery.

## Preferred failure injection

Use the least invasive mechanism supported by current infrastructure:

1. If the publisher schedule is enabled, disable only that regional rule/target.
2. If the schedule is intentionally disabled in dev, block normal publisher invocation and do not invoke it while creating work.
3. Do not change DynamoDB data manually.

## Sequence

1. Repository and Terraform validation.
2. Capture east/west health and Terraform outputs.
3. Confirm target worker mapping is enabled.
4. Confirm target processing queue baseline is zero or record preexisting work.
5. Confirm target publisher is not dispatching.
6. Submit N unique uploaded-resume analyses.
7. Assert each is accepted as `QUEUED_PENDING_DISPATCH`.
8. Assert processing queue does not grow from these submissions.
9. Query outbox through the existing sparse index contract; never scan.
10. Assert exactly N matching dispatchable events.
11. Restore/invoke publisher.
12. Assert queue receives/drains and analyses complete.
13. Assert unique IDs, no duplicate results, and terminal publisher state.
14. Capture logs and a no-drift plan.

## Safety cleanup

On EXIT, SIGINT, or SIGTERM restore publisher scheduling/activation to the initial state. Do not leave the worker disabled.
