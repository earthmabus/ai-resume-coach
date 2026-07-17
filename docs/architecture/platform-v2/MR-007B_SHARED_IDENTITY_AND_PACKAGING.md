# MR-007B — Shared Identity and Packaging Foundation

## Goal

Add the first deployable Platform V2 resources without introducing regional
application runtimes.

## Included

- shared Cognito user pool;
- shared web client;
- shared Cognito domain;
- shared registration-notification Lambda;
- SNS topic and optional email subscription;
- post-confirmation trigger;
- CloudWatch log retention;
- least-privilege SNS publishing policy;
- deterministic archives for all four isolated Lambda packages;
- identity inputs wired into both regional module contracts;
- Terraform tests proving both sites trust one identity issuer.

## Regional boundary

Identity is shared and exists once in `us-east-1`.

The registration-notification Lambda is shared because it is triggered by the
shared Cognito pool. It is not duplicated in east and west regional modules.

## Deferred

MR-007B does not create:

- regional APIs;
- DynamoDB tables;
- document buckets;
- SQS queues;
- workers;
- outbox publishers;
- regional monitoring;
- CloudFront;
- frontend hosting;
- Route 53 records.

## Offline validation

Extract the bundle and run:

```bash
./tools/validate_platform_v2_foundation.sh
```

The validator creates placeholder package directories, initializes Terraform
with the backend disabled, formats the copied configuration, validates it, and
runs Terraform tests.

## Acceptance criteria

- Terraform formatting passes.
- Terraform validation passes.
- Terraform tests pass.
- Exactly one shared Cognito user pool is defined.
- Exactly one registration-notification Lambda is defined.
- Both regional module instances receive the same issuer.
- Empty notification email creates no SNS subscription.
- All four Lambda package archives have deterministic hash outputs.
- No regional AWS runtime resources are introduced.
