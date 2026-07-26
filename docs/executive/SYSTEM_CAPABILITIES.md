# System Capabilities

> **Status:** Canonical
> **Audience:** Product leaders, engineering leaders, architects
> **Purpose:** State what the repository implements without expanding the product scope
> **Owner:** Product and Engineering Leadership
> **Related documents:** [Platform overview](PLATFORM_OVERVIEW.md), [product roadmap](PRODUCT_ROADMAP.md), [logical architecture](../architecture/03_LOGICAL_ARCHITECTURE.md)

## Functional Capabilities

- User authentication
- Career targeting
- Resume upload
- Resume analysis
- Resume tailoring
- Job matching

## Platform Capabilities

- Serverless deployment
- Active-active application sites in `us-east-1` and `us-west-2`
- DynamoDB MRSC state with an `us-east-2` witness
- Transactional outbox, idempotency, and explicit workflow state
- Deterministic processing ownership with regional queues and DLQs
- Regional document storage with optional asynchronous peer replication
- Infrastructure automation
- Bounded liveness and readiness checks
- Structured logging, metrics, dashboards, alarms, and synthetics
- Controlled recovery, evidence collection, and readiness profiles

## Quality Attributes

- Availability
- Security
- Scalability
- Maintainability
- Observability

## Explicit Boundaries

The repository does not claim automatic ownership transfer, automatic cross-region queue draining, seamless Cognito failover, immediate S3 consistency across regions, whole-account disaster recovery, contractual RTO/RPO, or production-profile certification.
