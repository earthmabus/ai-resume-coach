# MR-007C — Regional Storage and Messaging Foundation

## Goal

Create symmetric regional durability and asynchronous-processing boundaries
before adding application compute.

## Included per active Region

- private S3 document bucket;
- bucket-owner-enforced object ownership;
- complete public-access blocking;
- versioning;
- AES-256 server-side encryption;
- incomplete multipart cleanup after seven days;
- configurable noncurrent-version expiration;
- SQS processing queue;
- SQS processing dead-letter queue;
- 20-second long polling;
- SQS-managed encryption;
- configurable visibility, retention, and redrive settings;
- disabled EventBridge outbox-publisher schedule;
- API, worker, and outbox-publisher Lambda execution roles;
- AWSLambdaBasicExecutionRole attachments.

## Why the publisher schedules are disabled

MR-007C establishes the regional scheduling boundary but does not yet create
the outbox-publisher Lambdas. Enabling a schedule without a target would create
an incomplete operational path. The schedules remain disabled until the
publisher functions and EventBridge targets are introduced.

## Why DynamoDB is deferred

The selected target uses a multi-Region strongly consistent DynamoDB global
table with `us-east-2` as witness. That resource is a global data-plane concern
and must not be modeled as two independent regional tables. It will be
introduced in a dedicated slice with explicit replica and witness semantics.

## Why S3 replication is deferred

This slice creates the two regional buckets and their durability controls.
Replication requires cross-Region IAM, destination ownership, encryption, and
failure-observability decisions. Those are intentionally handled separately
rather than hidden inside the initial bucket creation.

## Deferred

- API Gateway;
- application Lambdas;
- DynamoDB MRSC global table;
- S3 cross-Region replication;
- EventBridge targets and Lambda permissions;
- queue event-source mappings;
- regional alarms and dashboards;
- CloudFront and Route 53.

## Acceptance criteria

- Terraform formatting and validation pass.
- All Terraform tests pass.
- East and west resource names are deterministic.
- Both buckets are private, encrypted, and versioned.
- Both processing queues use long polling and managed encryption.
- Both processing queues redrive to regional DLQs.
- Both publisher schedules exist but remain disabled.
- Three Lambda execution-role foundations exist per active Region.
- No API, application Lambda, DynamoDB, edge, or replication resource exists.
