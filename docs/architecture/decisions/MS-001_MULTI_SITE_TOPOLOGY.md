# MS-001: Multi-Site Topology

## Status

Accepted

## Decision

Operate two symmetric active application sites:

- `us-east-1`
- `us-west-2`

Use `us-east-2` as the DynamoDB MRSC witness region.

## Rationale

The design provides two active failure domains while preserving multi-region strong consistency for authoritative DynamoDB data.

Regional modules should remain symmetric peers. Site-specific values should be explicit and testable rather than inferred from accidental naming.

## Consequences

- Regional API and worker compute must receive equivalent configuration except for intentionally site-specific values.
- Routing, health, observability, deployment, and recovery behavior must account for both active sites.
- The witness region is not an application-serving site.
- Additional regional resources increase cost and operational surface area.
- Failover and restoration procedures must be validated, not merely described.
