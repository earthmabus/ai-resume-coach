# Operational Validation

> **Status:** Canonical operator index
> **Audience:** Operators, release engineers, auditors
> **Purpose:** Route safe checks and controlled exercises
> **Owner:** Operations
> **Related documents:** [Validation contract](../../engineering/VALIDATION_CONTRACT.md), [DR validation](../../mvp2-disaster-recovery/validation/README.md)

- Run repository validation from the [Validation Contract](../../engineering/VALIDATION_CONTRACT.md).
- Assess deployed resilience through the [MS-017 platform readiness tool](../../architecture/platform-resilience/MS-017_BASELINE_ASSESSMENT.md).
- Assess or exercise document continuity through [MS-022](../../architecture/platform-resilience/MS-022_DISASTER_RECOVERY_VALIDATION.md).
- Assess a named readiness profile through [MS-024A](../../architecture/platform-resilience/MS-024A_PRODUCTION_READINESS_PROFILES.md).
- Run controlled chaos only through the [MR-014 runbook](../platform-v2/MR-014/END_TO_END_CHAOS_CERTIFICATION_RUNBOOK.md) with explicit authorization.

Read-only assessment, bounded sentinel mutation, infrastructure deployment, and failure injection have different approval and evidence requirements.
