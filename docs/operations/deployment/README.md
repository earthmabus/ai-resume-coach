# Deployment

> **Status:** Canonical operator index
> **Audience:** Release engineers and operators
> **Purpose:** Route deployment and rollback work to supported procedures
> **Owner:** Operations
> **Related documents:** [Deployment architecture](../../architecture/11_DEPLOYMENT_ARCHITECTURE.md), [multi-site deployment runbook](../platform-v2/MULTI_SITE_DEPLOYMENT_RUNBOOK.md)

Use the [Multi-Site Deployment Runbook](../platform-v2/MULTI_SITE_DEPLOYMENT_RUNBOOK.md) for the current executable sequence. It validates first, changes one regional application at a time, verifies direct endpoints, and separates global routing changes.

Supporting references:

- [State and provider strategy](../../architecture/platform-v2/STATE_AND_PROVIDER_STRATEGY.md)
- [CI/CD and release model](../../architecture/platform-v2/CI_CD_AND_RELEASE_MODEL.md)
- [Failure, rollback, and recovery](../../architecture/platform-v2/FAILURE_ROLLBACK_AND_RECOVERY.md)
- [Validation contract](../../engineering/VALIDATION_CONTRACT.md)

The older teardown-and-rebuild record is not the primary procedure for normal releases.
