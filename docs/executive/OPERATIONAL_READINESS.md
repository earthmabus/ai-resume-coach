# Operational Readiness

> **Status:** Canonical
> **Audience:** Engineering leaders, operators, auditors
> **Purpose:** Distinguish implemented architecture, tested recovery, and environment certification
> **Owner:** Operations and Engineering Leadership
> **Related documents:** [Validation and certification](../architecture/12_VALIDATION_AND_CERTIFICATION.md), [certification portal](../certification/README.md), [operations portal](../operations/README.md)

Operational readiness measures whether a specific environment can be deployed, observed, operated, and recovered under an explicit policy. It is not a synonym for architecture completion.

The repository provides:

- Infrastructure automation
- direct and global health validation;
- structured logs and correlation;
- dashboards, curated alarms, and synthetic health checks when enabled;
- queue, DLQ, regional isolation, and evidence runbooks;
- read-only resilience assessments and approval-gated failure exercises;
- durable multi-site failure certification;
- development, integration, pre-production, and production readiness profiles.

The architecture and controlled failure envelope are complete. MR-014 passed four of four scenarios and is the authoritative runtime certification. The current durable readiness record passes the pre-production profile with documented lower-environment exceptions.

Production certification remains unclaimed. The production profile requires Cognito WAF, alarm notification actions, and Terraform production-readiness enforcement in addition to the controls required by every profile. Enabling cost-bearing controls requires explicit approval and deployed evidence.
