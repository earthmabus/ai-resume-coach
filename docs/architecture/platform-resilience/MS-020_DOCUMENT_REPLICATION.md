# MS-020 — Cross-Region Document Replication

## Status

Implementation overlay prepared. Deployment requires a reviewed saved Terraform plan.

## Decision

Enable **bidirectional S3 Cross-Region Replication (CRR)** between the existing
regional document buckets:

- `us-east-1` → `us-west-2`
- `us-west-2` → `us-east-1`

Both sites are active and may accept uploads through global API routing. A
one-way primary/replica model would therefore leave documents written in the
other active site without a regional copy.

## Scope

MS-020 adds:

- one least-privilege S3 replication role and policy per source site;
- one replication configuration per regional bucket;
- replication of new object versions, tags, and delete markers;
- explicit Terraform outputs describing replication behavior and limitations;
- plan/apply/validate tooling with evidence capture;
- Terraform and Python contract tests.

The existing buckets already use:

- versioning;
- S3-managed AES-256 encryption (`SSE-S3`);
- Bucket Owner Enforced object ownership;
- public-access blocking.

These controls are preserved.

## Important limitations

### Existing objects are not backfilled

Ordinary S3 CRR applies to object versions created after replication is enabled.
Objects already present in either bucket require a separate S3 Batch Replication
or controlled copy operation. MS-020 deliberately does not perform that
mutation automatically.

### Replication is asynchronous

The contract is `BEST_EFFORT`. S3 Replication Time Control is disabled because
it adds cost and was not required for this development environment. Applications
must not assume a newly uploaded object is immediately available in the peer
Region.

### Replicas do not create loops

S3 does not recursively replicate replica objects under ordinary replication
rules. The bidirectional configuration therefore covers original writes in both
active Regions without creating an infinite replication loop.

## Activation

```bash
./tools/resilience/activate_document_replication.sh plan

CONFIRM_MUTATION=YES \
  ./tools/resilience/activate_document_replication.sh apply

./tools/resilience/activate_document_replication.sh validate
```

The activation plan explicitly preserves the previously deployed MS-018 global
routing and MS-019 Cognito recovery controls.

## Validation contract

Validation confirms:

1. both buckets remain versioned;
2. each bucket has an enabled replication rule;
3. each rule targets the opposite regional bucket;
4. the Terraform output reports bidirectional replication;
5. existing-object backfill and RTC remain explicitly false.

## Follow-up

A later operational slice may add:

- an intentional existing-object backfill runbook;
- object-level replication probes;
- replication-lag alarms if the cost is approved;
- application read fallback and ownership semantics.
