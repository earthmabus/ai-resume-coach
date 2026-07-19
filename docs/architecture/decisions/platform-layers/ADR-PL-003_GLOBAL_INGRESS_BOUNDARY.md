# ADR-PL-003: Global Ingress Boundary

Status: Proposed

## Decision

Global ingress is a separate layer and implementation slice. It will own:

- Regional API custom domains.
- Regional ACM certificates.
- Route 53 latency records and optional health checks.
- Site-level routing enablement and isolation controls.
- DNS validation and rollback procedures.

It consumes regional API endpoints and health contracts but does not own regional compute or shared data.

Global routing remains disabled by default until the layer has independent acceptance tests and a reversible isolation exercise.
