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

## Outbox schedule

The table and publisher permissions now exist, but the EventBridge schedule
remains disabled. The package in this foundation bundle is still a placeholder;
the schedule should be enabled only after the real outbox-publisher code and
end-to-end idempotency tests are installed.

## Deferred

- API Gateway and Cognito authorizer
- application source-package integration
- outbox schedule activation
- DynamoDB Streams
- cross-Region S3 replication
- CloudFront and Route 53 routing
- alarms, dashboards, and recovery exercises
