# Platform Overview

> **Status:** Canonical
> **Audience:** Engineering leaders, product leaders, hiring managers
> **Purpose:** Connect the user journey to the major platform responsibilities
> **Owner:** Product and Engineering Leadership
> **Related documents:** [Executive summary](EXECUTIVE_SUMMARY.md), [system capabilities](SYSTEM_CAPABILITIES.md), [technical platform overview](../architecture/02_PLATFORM_OVERVIEW.md)

AI Resume Coach is organized around a straightforward user journey:

1. A user authenticates securely.
2. The user establishes career goals.
3. Resume evidence is uploaded.
4. AI analyzes the resume.
5. Recommendations are generated.
6. Tailored resumes and job matching assist the user's job search.

The browser experience calls authenticated regional APIs. Domain services validate commands and persist authoritative state. Asynchronous workflows are committed before transport, delivered through regional queues, and processed by the worker authorized by durable ownership. Provider abstractions integrate AI analysis without making an external provider the system of record.

Global routing and peer application sites improve availability. Strongly consistent DynamoDB state, asynchronous document replication, warm-standby identity recovery, and explicit regional processing ownership each have different consistency and recovery behavior; the platform does not collapse them into a vague “multi-region” claim.

Operations are part of the product platform. Structured logs, health endpoints, metrics, dashboards, alarms, synthetics, runbooks, controlled failure exercises, and certification records support deployment and incident response. Cost-bearing controls remain explicit and environment-specific.

The governing design philosophy is simple: managed services over undifferentiated operations, durable semantics over implicit failover, automation over undocumented procedure, and certification evidence over architectural assertion.
