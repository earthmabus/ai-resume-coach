# Security Architecture

> **Status:** Canonical
> **Audience:** Security reviewers, architects, developers, operators
> **Purpose:** Define trust, authorization, privacy, and recovery boundaries
> **Owner:** Platform Engineering
> **Related documents:** [Physical architecture](04_PHYSICAL_ARCHITECTURE.md), [observability](10_OBSERVABILITY.md), [incident response](../operations/production/INCIDENT_RESPONSE_AND_REVIEW.md)

## Authentication and authorization

Cognito JWT authorization protects product routes at the regional HTTP APIs. Authentication proves the caller identity accepted by the configured authorizer. Runtime region, site, deployment identifiers, request IDs, and correlation IDs are diagnostics; they are not authorization, tenancy, or routing inputs.

The development synthetic-placement override exists only for deterministic validation. It is feature-gated and restricted to an authorized Cognito group. It is not a production work-routing mechanism.

## Data protection

The architecture keeps authoritative state in DynamoDB and documents in private regional S3 buckets. Bucket public access is blocked, object ownership is enforced, versioning is enabled, and the documented deployment uses server-side encryption. Access is granted through scoped IAM roles and policies rather than public storage.

Evidence and durable documentation must exclude tokens, secrets, account identifiers, ARNs, physical table or bucket names, queue URLs, resume text, job descriptions, prompts, provider payloads, sensitive presigned material, and raw exception bodies.

## Edge and operational controls

Route 53 health checks and regional readiness endpoints support routing decisions without exposing internal resource identifiers. CloudWatch logging, alarms, dashboards, and synthetics are cost-gated controls. Cognito WAF is required by the production readiness profile but optional or recommended in lower profiles; its absence must not be confused with architectural incompleteness.

## Recovery boundary

The west-region Cognito recovery foundation is warm standby, not seamless identity failover. Password verifiers and active sessions are not replicated. Recovery requires controlled user-attribute migration, authorizer/client reconfiguration, and password resets. Operators must communicate this user impact rather than describe identity as active-active.

Security incidents follow the [incident response and review process](../operations/production/INCIDENT_RESPONSE_AND_REVIEW.md). Recovery actions remain approval-gated and must preserve evidence.
