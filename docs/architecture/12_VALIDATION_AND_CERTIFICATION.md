# Validation and Certification

> **Status:** Canonical
> **Audience:** Engineering leaders, developers, auditors, operators
> **Purpose:** Explain how repository correctness, runtime resilience, and readiness are proven
> **Owner:** Platform Engineering and Operations
> **Related documents:** [Validation contract](../engineering/VALIDATION_CONTRACT.md), [certification portal](../certification/README.md), [operational readiness](../executive/OPERATIONAL_READINESS.md)

Validation and certification answer different questions:

- **Repository validation** checks Python, tests, Terraform formatting and validity, architecture contracts, and platform foundation rules.
- **Runtime validation** checks deployed health, routing, queues, workers, replication, and other control-plane facts.
- **Failure certification** executes approved bounded disruption and records observed recovery behavior.
- **Readiness certification** evaluates an environment against a named policy profile.

The multi-site architecture completed MR-014 failure certification on July 22, 2026. Four scenarios passed: the both-sites-disabled guard, bidirectional routing isolation with survivor work, worker interruption with durable backlog and recovery, and post-recovery reconciliation. The durable result is [MR-014](../certification/MR-014_MULTI_SITE_CERTIFICATION.md).

The current durable readiness record is a passing pre-production profile. It retains warnings for controls that the production profile requires, including Cognito WAF, alarm notification actions, and Terraform production enforcement. `profileReady` for pre-production is not `productionReady`.

Evidence must identify its deployment, environment, commands, results, limitations, and sanitized artifacts. A milestone plan or expected result is not certification. Formal records remain intact under `docs/certification/`; implementation plans and reports remain traceability material.

Before declaring a documentation or implementation slice complete, follow the [validation contract](../engineering/VALIDATION_CONTRACT.md). Do not weaken executable tests to reconcile prose.
