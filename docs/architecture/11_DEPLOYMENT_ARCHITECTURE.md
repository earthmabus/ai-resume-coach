# Deployment Architecture

> **Status:** Canonical
> **Audience:** Developers, release engineers, operators
> **Purpose:** Explain deployment units, ordering, state, and rollback boundaries
> **Owner:** Platform Engineering and Operations
> **Related documents:** [Deployment runbook](../operations/deployment/README.md), [state and provider strategy](platform-v2/STATE_AND_PROVIDER_STRATEGY.md), [validation contract](../engineering/VALIDATION_CONTRACT.md)

Terraform composes shared/global capabilities and two symmetric regional application modules. Regional providers target `us-east-1` and `us-west-2`; the MRSC table additionally records the `us-east-2` witness responsibility. Shared state and provider wiring are explicit so regional resources do not accidentally migrate between providers.

Application packages are built through `tools/build/lambda_packages.py`; root `handler.py` and `worker.py` remain thin compatibility entrypoints. Deployment identity is diagnostic metadata propagated into regional runtimes and evidence.

The safe release sequence is:

```text
validate → plan → deploy one site → verify its direct endpoint
         → deploy the peer → verify its direct endpoint
         → change global routing separately → reconcile
```

Routing activation, document replication, identity recovery, observability, and production readiness use explicit feature inputs and reviewable plans. Mutating resilience tools require confirmation and write evidence. Cost-bearing controls remain gated.

Rollback is scoped to the affected regional package or configuration. Do not treat infrastructure rollback as a way to reverse durable business data. Route restoration and worker restoration have separate verification steps because an accepted control-plane request is not proof of completed recovery.

The executable deployment procedure is the [multi-site deployment runbook](../operations/platform-v2/MULTI_SITE_DEPLOYMENT_RUNBOOK.md). Historical teardown instructions remain implementation records and are not the primary current procedure.
