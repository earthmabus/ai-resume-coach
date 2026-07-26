# MS-022 — Automated Disaster-Recovery Validation

## Decision

MS-022 adds a repeatable evidence-producing disaster-recovery validation tool.
It verifies the deployed east and west control planes and can exercise the
bidirectional S3 data path with bounded sentinel objects.

This is **not a destructive regional-outage exercise**. It does not disable
Route 53 records or health checks, stop Lambda event sources, modify queues,
make DynamoDB unavailable, or switch Cognito identity providers.

## Modes

### Read-only assessment

```bash
./tools/resilience/activate_disaster_recovery_validation.sh assess
```

The assessment checks:

- the global routing and health-check contract;
- both regional `/health/live` and `/health/ready` endpoints;
- the global `/health/ready` endpoint;
- both regional worker deployment states;
- both regional processing queues;
- warm-standby Cognito recovery semantics;
- bidirectional document-replication configuration;
- fail-closed persisted processing ownership.

### Bounded data-path exercise

```bash
CONFIRM_MUTATION=YES \
  ./tools/resilience/activate_disaster_recovery_validation.sh exercise
```

The exercise performs all assessment checks, then writes one unique sentinel to
each regional document bucket. Each object must become readable from the peer
Region within a bounded polling window. The tool then attempts cleanup in both
buckets.

The exercise only proves replication of **new objects created during the
exercise**. It does not backfill or validate objects that existed before CRR was
enabled.

## Evidence

Each run creates a timestamped directory under `evidence/` containing:

- Terraform outputs used as the contract source;
- regional and global health responses;
- Lambda configuration evidence;
- queue attributes;
- S3 sentinel and replication evidence when exercise mode is used;
- `checks.jsonl`;
- a concise `report.txt`;
- a machine-readable `report.json`.

## Identity boundary

Cognito is considered recoverable through the MS-019 warm-standby contract:
user attributes can be imported and users must reset passwords. Passwords and
active sessions do not replicate, and MS-022 does not claim seamless or
automated identity failover.

## Processing-ownership boundary

MS-022 validates the MS-021 contract but does not change `ownerRegion`, drain a
failed regional queue, or redispatch work. Controlled owner transfer remains a
separate operator procedure.

## What a later destructive game day would add

A production-authorized game day could isolate one API route, stop one event
source mapping, execute controlled owner transfer and redispatch, and measure
RTO/RPO. Those mutations require a separate milestone, explicit rollback steps,
and a maintenance window.
