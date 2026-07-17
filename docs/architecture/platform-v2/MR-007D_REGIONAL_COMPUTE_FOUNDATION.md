# MR-007D — Regional Compute Foundation

## Goal

Create symmetric regional application compute and connect it to the storage
and messaging boundaries introduced by MR-007C.

## Included per active Region

- API Lambda;
- asynchronous worker Lambda;
- transactional-outbox publisher Lambda;
- explicit CloudWatch log groups with configurable retention;
- SQS event-source mapping for the worker;
- partial-batch failure reporting;
- EventBridge target and Lambda permission for the outbox publisher;
- deterministic runtime, architecture, memory, and timeout configuration;
- shared Cognito, regional bucket, and regional queue environment wiring;
- least-privilege S3 and SQS runtime policies.

## Operational state

The worker event-source mapping is enabled because its regional processing
queue exists and its permissions are complete.

The outbox publisher function and EventBridge target exist, but the associated
schedule remains disabled. The publisher cannot be operationally complete
until the DynamoDB MRSC table and outbox permissions are introduced.

The API Lambda exists but is not externally reachable because API Gateway is
intentionally deferred.

## Deferred

- API Gateway and Cognito JWT authorizer;
- DynamoDB MRSC global table and witness;
- DynamoDB access policies;
- outbox query and state-transition permissions;
- S3 cross-Region replication;
- CloudFront and Route 53;
- alarms, dashboards, and synthetic checks.

## Acceptance criteria

- All prior Terraform tests remain green.
- Three deterministic Lambda functions exist per active Region.
- All functions use the same configured runtime and architecture.
- Explicit log groups exist with finite retention.
- Workers consume only their regional queues.
- Worker event-source mappings support partial-batch failures.
- EventBridge can invoke each regional outbox publisher.
- Outbox schedules remain disabled.
- APIs remain private until API Gateway is added.
