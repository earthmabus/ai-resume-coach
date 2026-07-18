# MS-002: Retain the Current Single DynamoDB Table

## Status

Accepted for the current platform stage

## Decision

Keep the existing single DynamoDB table instead of splitting data into multiple tables at this time.

## Rationale

The current design benefits from:

- existing access patterns
- simpler transactional writes
- co-location of domain state, idempotency, and outbox records
- simpler MRSC configuration
- lower Terraform, IAM, monitoring, backup, and operational complexity
- lower migration risk while multi-site work is being completed

## Rejected Alternatives

### One table per entity

Rejected because it would reproduce relational entity decomposition without DynamoDB joins and would create unnecessary operational complexity.

### Immediate bounded-context decomposition

Deferred because current evidence does not yet justify the migration and coordination cost.

## Revisit When

Reconsider table boundaries when capabilities demonstrate materially different:

- ownership
- access patterns
- transaction boundaries
- retention policies
- security needs
- scaling profiles
- resilience tiers
- deployment lifecycles
- compliance obligations

Any future split should use single-table design within meaningful bounded operational domains rather than defaulting to one table per record type.
