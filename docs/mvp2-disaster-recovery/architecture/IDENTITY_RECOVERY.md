# Identity Recovery

> **Status:** Canonical
> **Audience:** Architects, security reviewers, operators
> **Purpose:** State the Cognito recovery model without overstating availability
> **Owner:** Platform Engineering and Security
> **Related documents:** [Security architecture](../../architecture/05_SECURITY_ARCHITECTURE.md), [MS-019](../../architecture/platform-resilience/MS-019_IDENTITY_RECOVERY.md)

Normal application traffic uses the shared Cognito user pool and its regional issuer. Amazon Cognito user pools do not natively replicate password verifiers, refresh tokens, hosted domains, pool IDs, client IDs, or issuers across regions.

The repository therefore models a warm-standby user pool, client, and hosted domain in `us-west-2`. It preserves the user-facing attribute and authentication-flow contract, but it is not connected as automatic failover.

Recovery requires an approved migration of available user attributes, updates to authorizer and frontend configuration, and password resets for restored users. Existing sessions do not survive. Operators must include this disruption in incident communication and recovery evidence.

Traceability: [MS-019 identity recovery](../../architecture/platform-resilience/MS-019_IDENTITY_RECOVERY.md), [readiness profiles](../../architecture/platform-resilience/MS-024A_PRODUCTION_READINESS_PROFILES.md), and [production certification boundary](../../architecture/platform-resilience/MS-024_PRODUCTION_READINESS_CERTIFICATION.md).
