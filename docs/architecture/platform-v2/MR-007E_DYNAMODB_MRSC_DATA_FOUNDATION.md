# MR-007E — DynamoDB MRSC Data Foundation

## Goal

Introduce the shared multi-Region strongly consistent system of record for
Platform V2 and wire both regional compute sites to their local replicas.

## Topology

- Primary Terraform-managed replica: `us-east-1`
- Peer active replica: `us-west-2`
- Witness: `us-east-2`
- Consistency mode: `STRONG`
- Billing: `PAY_PER_REQUEST`
- Key schema: string partition key `pk`, string sort key `sk`

The witness participates in MRSC availability but does not expose a readable
or writable application table.

## Resilience and security

- Point-in-time recovery is enabled on both active replicas.
- Server-side encryption uses the DynamoDB service-managed KMS key.
- Deletion protection is configurable and defaults to `false` for development.
- Tags are propagated to the peer replica.
- TTL is intentionally omitted because MRSC global tables do not support TTL.
- Streams are intentionally deferred; MRSC replication does not require them.

## Runtime wiring

All regional functions receive:

- `APPLICATION_TABLE`
- `DATA_CONSISTENCY=STRONG`
- `DATA_WITNESS_REGION=us-east-2`

Each regional execution role receives access to the regional table ARN and its
indexes. The API, worker, and outbox publisher receive only the DynamoDB actions
required by their current responsibilities.

## Sparse `gsi1` contract

The table exposes one sparse global secondary index used by the current
single-table runtime query model:

- index name: `gsi1`
- partition key: `gsi1pk`, string
- sort key: `gsi1sk`, string
- projection: `ALL`

Only items that require indexed access populate both attributes. Domain entity
records use `ENTITY#<entityId>` for by-entity lookup. Dispatchable outbox records
use status partitions such as `OUTBOX_STATUS#PENDING`, with `gsi1sk` ordered by
creation timestamp and event ID. Terminal outbox states remove the dispatch GSI
keys. Base-key-only records, including idempotency records, intentionally omit
the attributes.

`ALL` projection is accepted because entity lookup paths return the indexed item
directly, and the outbox publisher needs complete event payload, ownership,
version, request, correlation, and dispatch fields without follow-up reads. The
outbox status partition is acceptable for the current development validation
scale and must be revisited before high-volume production scheduling.

## Outbox schedule

The table, publisher permissions, real outbox-publisher package, and
idempotency/outbox tests now exist. EventBridge schedule activation is
controlled by `enable_outbox_publisher_schedule`, which defaults to `false`.
Development runtime validation may explicitly enable it after verifying
publisher duplicate-dispatch safety and IAM scope.

## Deferred

- API Gateway and Cognito authorizer
- application source-package integration
- production outbox schedule activation decision
- DynamoDB Streams
- cross-Region S3 replication
- CloudFront and Route 53 routing
- alarms, dashboards, and recovery exercises
