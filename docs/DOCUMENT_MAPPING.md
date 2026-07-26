# Documentation Mapping

> **Status:** Canonical migration inventory
> **Audience:** Documentation maintainers, reviewers, auditors
> **Purpose:** Classify every repository Markdown file and record its durable destination
> **Owner:** Documentation Maintainers
> **Related documents:** [Document index](DOCUMENT_INDEX.md), [migration guide](MIGRATION_GUIDE.md)

## How to read this inventory

Every row records current path, proposed path, status, replacement or canonical destination, and unique-content disposition. Each section supplies the classification, audience, purpose, and rationale inherited by its rows. “Same” means the proposed path is the current path. “Preserved” means the source remains or its unique content is represented at the named canonical destination. There are no pending-review entries.

### Canonical

**Audience:** the audience named by each publication metadata header.
**Purpose:** current primary guidance, navigation, or governance.
**Rationale:** these documents own durable concepts and minimize duplicated prose.

| Current path | Proposed path | Status | Canonical destination | Unique content |
|---|---|---|---|---|
| `README.md` | Same | Active landing page | Self | Preserved |
| `docs/README.md` | Same | Active portal | Self | Preserved |
| `docs/DOCUMENT_INDEX.md` | Same | Active index | Self | Preserved |
| `docs/DOCUMENT_MAPPING.md` | Same | Active inventory | Self | Preserved |
| `docs/MIGRATION_GUIDE.md` | Same | Active guide | Self | Preserved |
| `docs/executive/README.md` | Same | Active index | Self | Preserved |
| `docs/executive/EXECUTIVE_SUMMARY.md` | Same | Active publication | Self | Preserved |
| `docs/executive/PLATFORM_OVERVIEW.md` | Same | Active publication | Self | Preserved |
| `docs/executive/SYSTEM_CAPABILITIES.md` | Same | Active publication | Self | Preserved |
| `docs/executive/OPERATIONAL_READINESS.md` | Same | Active publication | Self | Preserved |
| `docs/executive/PRODUCT_ROADMAP.md` | Same | Active planning publication | Self | Preserved |
| `docs/executive/GLOSSARY.md` | Same | Active reference | Self | Preserved |
| `docs/architecture/README.md` | Same | Active index | Self | Preserved |
| `docs/architecture/DOCUMENT_INDEX.md` | Same | Active index | Self | Preserved |
| `docs/architecture/01_EXECUTIVE_OVERVIEW.md` | Same | Active publication | Self | Preserved |
| `docs/architecture/02_PLATFORM_OVERVIEW.md` | Same | Active publication | Self | Preserved |
| `docs/architecture/03_LOGICAL_ARCHITECTURE.md` | Same | Active publication | Self | Preserved |
| `docs/architecture/04_PHYSICAL_ARCHITECTURE.md` | Same | Active publication | Self | Preserved |
| `docs/architecture/05_SECURITY_ARCHITECTURE.md` | Same | Active publication | Self | Preserved |
| `docs/architecture/06_REQUEST_LIFECYCLE.md` | Same | Active publication | Self | Preserved |
| `docs/architecture/07_DATA_ARCHITECTURE.md` | Same | Active publication | Self | Preserved |
| `docs/architecture/08_PROCESSING_ARCHITECTURE.md` | Same | Active publication | Self | Preserved |
| `docs/architecture/09_DISASTER_RECOVERY.md` | Same | Active publication | Self | Preserved |
| `docs/architecture/10_OBSERVABILITY.md` | Same | Active publication | Self | Preserved |
| `docs/architecture/11_DEPLOYMENT_ARCHITECTURE.md` | Same | Active publication | Self | Preserved |
| `docs/architecture/12_VALIDATION_AND_CERTIFICATION.md` | Same | Active publication | Self | Preserved |
| `docs/architecture/13_OPERATIONAL_RUNBOOK.md` | Same | Active publication | Self | Preserved |
| `docs/architecture/14_ARCHITECTURAL_DECISIONS.md` | Same | Active publication | Self | Preserved |
| `docs/mvp2-disaster-recovery/README.md` | Same | Active publication home | Self | Preserved |
| `docs/mvp2-disaster-recovery/architecture/README.md` | Same | Active index | Self | Preserved |
| `docs/mvp2-disaster-recovery/architecture/TOPOLOGY_AND_ROUTING.md` | Same | Active publication | Self | Preserved |
| `docs/mvp2-disaster-recovery/architecture/IDENTITY_RECOVERY.md` | Same | Active publication | Self | Preserved |
| `docs/mvp2-disaster-recovery/architecture/DATA_CONSISTENCY.md` | Same | Active publication | Self | Preserved |
| `docs/mvp2-disaster-recovery/architecture/PROCESSING_OWNERSHIP.md` | Same | Active publication | Self | Preserved |
| `docs/mvp2-disaster-recovery/operations/README.md` | Same | Active index | Self | Preserved |
| `docs/mvp2-disaster-recovery/operations/REGIONAL_RECOVERY.md` | Same | Active routing guide | Self | Preserved |
| `docs/mvp2-disaster-recovery/validation/README.md` | Same | Active index | Self | Preserved |
| `docs/mvp2-disaster-recovery/certification/README.md` | Same | Active index | Self | Preserved |
| `docs/mvp2-disaster-recovery/diagrams/README.md` | Same | Active asset index | Self | Preserved |
| `docs/operations/README.md` | Same | Active portal | Self | Preserved |
| `docs/operations/deployment/README.md` | Same | Active index | Self | Preserved |
| `docs/operations/monitoring/README.md` | Same | Active index | Self | Preserved |
| `docs/operations/incident-response/README.md` | Same | Active index | Self | Preserved |
| `docs/operations/runbooks/README.md` | Same | Active index | Self | Preserved |
| `docs/operations/runbooks/QUEUE_AND_DLQ.md` | Same | Active routing guide | Self | Preserved |
| `docs/operations/validation/README.md` | Same | Active index | Self | Preserved |
| `docs/certification/README.md` | Same | Active index | Self | Preserved |
| `docs/engineering/README.md` | Same | Active index | Self | Preserved |
| `docs/product/README.md` | Same | Active index | Self | Preserved |
| `docs/reference/README.md` | Same | Active index | Self | Preserved |
| `docs/reference/GLOSSARY.md` | Same | Active reference | Self | Preserved |
| `docs/history/README.md` | Same | Active historical index | Self | Preserved |

### Keep

**Audience:** contributors, architects, operators, auditors, or portfolio readers according to path.
**Purpose:** preserve durable repository guidance, decisions, detailed runbooks, formal evidence, templates, history, archive manifests, and portfolio material.
**Rationale:** each file has procedural, decision, evidence, instructional, or chronological detail that should not be flattened into canonical summaries.

| Current path | Proposed path | Status | Canonical destination | Unique content |
|---|---|---|---|---|
| `AGENTS.md` | Same | Active repository guidance | Self | Preserved |
| `docs/architecture/REPOSITORY_STRUCTURE.md` | Same | Active reference | Self; `docs/reference/REPOSITORY_STRUCTURE.md` routes here | Preserved |
| `docs/architecture/TOOLING_TAXONOMY.md` | Same | Active reference | Self; `docs/reference/TOOLING_TAXONOMY.md` routes here | Preserved |
| `docs/architecture/active-active/MR-006_REGIONAL_AWARENESS.md` | Same | Milestone record | `docs/architecture/06_REQUEST_LIFECYCLE.md` | Preserved |
| `docs/architecture/decisions/ADR-001_SERVERLESS_ARCHITECTURE.md` | Same | Accepted decision | Self | Preserved |
| `docs/architecture/decisions/MR-013_EXPLICIT_WORKFLOW_STATE_MACHINE.md` | Same | Accepted decision | Self | Preserved |
| `docs/architecture/decisions/MS-001_MULTI_SITE_TOPOLOGY.md` | Same | Accepted decision | Self | Preserved |
| `docs/architecture/decisions/MS-002_SINGLE_TABLE_FOR_NOW.md` | Same | Accepted decision | Self | Preserved |
| `docs/architecture/decisions/MS-003_SHARED_PROCESSING_CAPABILITY.md` | Same | Accepted decision | Self | Preserved |
| `docs/architecture/decisions/MS-004_RUNTIME_IDENTITY.md` | Same | Accepted decision | Self | Preserved |
| `docs/architecture/decisions/MS-005_WORK_OWNERSHIP_AND_PLACEMENT.md` | Same | Accepted decision | Self | Preserved |
| `docs/architecture/decisions/MS-006_CROSS_REGION_TRANSPORT_FOUNDATION.md` | Same | Accepted decision | Self | Preserved |
| `docs/architecture/decisions/MS-007_CORRELATION_AND_TRACEABILITY.md` | Same | Accepted decision | Self | Preserved |
| `docs/architecture/decisions/MS-008_REGIONAL_HEALTH_CLASSIFICATION.md` | Same | Accepted decision | Self | Preserved |
| `docs/architecture/decisions/MS-009_DEVELOPMENT_SYNTHETIC_PLACEMENT_OVERRIDE.md` | Same | Accepted decision | Self | Preserved |
| `docs/architecture/decisions/MS-010_OUTBOX_PUBLISHER_SCHEDULE_ACTIVATION.md` | Same | Accepted decision | Self | Preserved |
| `docs/architecture/decisions/platform-layers/ADR-PL-001_PLATFORM_LAYERING_MODEL.md` | Same | Accepted decision | Self | Preserved |
| `docs/architecture/decisions/platform-layers/ADR-PL-002_SHARED_FOUNDATION_BOUNDARY.md` | Same | Accepted decision | Self | Preserved |
| `docs/architecture/decisions/platform-layers/ADR-PL-003_GLOBAL_INGRESS_BOUNDARY.md` | Same | Accepted decision | Self | Preserved |
| `docs/architecture/decisions/platform-layers/ADR-PL-004_PRODUCTION_OPERATIONS_OVERLAY.md` | Same | Accepted decision | Self | Preserved |
| `docs/architecture/decisions/platform-layers/README.md` | Same | Decision index | Self | Preserved |
| `docs/architecture/decisions/platform-layers/REVIEW_CHECKLIST.md` | Same | Review aid | Self | Preserved |
| `docs/architecture/decisions/platform-layers/SHARED_FOUNDATION_CHANGE_PLAN.md` | Same | Change record | Platform-layer ADR package | Preserved |
| `docs/architecture/platform-resilience/MS-017_BASELINE_ASSESSMENT.md` | Same | Historical baseline method | `docs/mvp2-disaster-recovery/validation/README.md` | Preserved |
| `docs/architecture/platform-resilience/MS-018_GLOBAL_API_ROUTING.md` | Same | Implementation record | `docs/mvp2-disaster-recovery/architecture/TOPOLOGY_AND_ROUTING.md` | Preserved |
| `docs/architecture/platform-resilience/MS-019_IDENTITY_RECOVERY.md` | Same | Implementation record | `docs/mvp2-disaster-recovery/architecture/IDENTITY_RECOVERY.md` | Preserved |
| `docs/architecture/platform-resilience/MS-020_DOCUMENT_REPLICATION.md` | Same | Implementation record | `docs/mvp2-disaster-recovery/architecture/DATA_CONSISTENCY.md` | Preserved |
| `docs/architecture/platform-resilience/MS-021_PROCESSING_OWNERSHIP.md` | Same | Implementation record | `docs/mvp2-disaster-recovery/architecture/PROCESSING_OWNERSHIP.md` | Preserved |
| `docs/architecture/platform-resilience/MS-022_DISASTER_RECOVERY_VALIDATION.md` | Same | Validation contract | `docs/mvp2-disaster-recovery/validation/README.md` | Preserved |
| `docs/architecture/platform-resilience/MS-023_PRODUCTION_OBSERVABILITY.md` | Same | Implementation record | `docs/architecture/10_OBSERVABILITY.md` | Preserved |
| `docs/architecture/platform-resilience/MS-024A_PRODUCTION_READINESS_PROFILES.md` | Same | Readiness policy | `docs/architecture/12_VALIDATION_AND_CERTIFICATION.md` | Preserved |
| `docs/architecture/platform-resilience/MS-024_PRODUCTION_READINESS_CERTIFICATION.md` | Same | Certification contract | `docs/architecture/12_VALIDATION_AND_CERTIFICATION.md` | Preserved |
| `docs/architecture/platform-v2/ACCEPTANCE_CRITERIA.md` | Same | Acceptance contract | `docs/architecture/12_VALIDATION_AND_CERTIFICATION.md` | Preserved |
| `docs/architecture/platform-v2/ARCHITECTURE_DECISIONS.md` | Same | Decision summary | `docs/architecture/14_ARCHITECTURAL_DECISIONS.md` | Preserved |
| `docs/architecture/platform-v2/CI_CD_AND_RELEASE_MODEL.md` | Same | Release reference | `docs/architecture/11_DEPLOYMENT_ARCHITECTURE.md` | Preserved |
| `docs/architecture/platform-v2/DATA_AND_REGION_BOUNDARIES.md` | Same | Architecture record | `docs/architecture/07_DATA_ARCHITECTURE.md` | Preserved |
| `docs/architecture/platform-v2/DEPLOYMENT_AND_REBUILD_RUNBOOK.md` | Same | Historical rebuild procedure | `docs/operations/deployment/README.md` | Preserved |
| `docs/architecture/platform-v2/FAILURE_ROLLBACK_AND_RECOVERY.md` | Same | Architecture record | `docs/architecture/11_DEPLOYMENT_ARCHITECTURE.md` | Preserved |
| `docs/architecture/platform-v2/MODULE_SPECIFICATION.md` | Same | Terraform design reference | `docs/architecture/04_PHYSICAL_ARCHITECTURE.md` | Preserved |
| `docs/architecture/platform-v2/MR-007A_PLATFORM_V2_FOUNDATION.md` | Same | Milestone record | `docs/architecture/04_PHYSICAL_ARCHITECTURE.md` | Preserved |
| `docs/architecture/platform-v2/MR-007B_SHARED_IDENTITY_AND_PACKAGING.md` | Same | Milestone record | `docs/architecture/04_PHYSICAL_ARCHITECTURE.md` | Preserved |
| `docs/architecture/platform-v2/MR-007C_REGIONAL_STORAGE_AND_MESSAGING.md` | Same | Milestone record | `docs/architecture/04_PHYSICAL_ARCHITECTURE.md` | Preserved |
| `docs/architecture/platform-v2/MR-007D_REGIONAL_COMPUTE_FOUNDATION.md` | Same | Milestone record | `docs/architecture/04_PHYSICAL_ARCHITECTURE.md` | Preserved |
| `docs/architecture/platform-v2/MR-007E_DYNAMODB_MRSC_DATA_FOUNDATION.md` | Same | Milestone record | `docs/architecture/07_DATA_ARCHITECTURE.md` | Preserved |
| `docs/architecture/platform-v2/MR-007F_REGIONAL_API_GATEWAY_FOUNDATION.md` | Same | Milestone record | `docs/architecture/04_PHYSICAL_ARCHITECTURE.md` | Preserved |
| `docs/architecture/platform-v2/MR-007G_GLOBAL_ACTIVE_ACTIVE_API_ROUTING.md` | Same | Milestone record | `docs/mvp2-disaster-recovery/architecture/TOPOLOGY_AND_ROUTING.md` | Preserved |
| `docs/architecture/platform-v2/MR-007H_EDGE_SECURITY_FOUNDATION.md` | Same | Milestone record | `docs/architecture/05_SECURITY_ARCHITECTURE.md` | Preserved |
| `docs/architecture/platform-v2/MR-007I_OBSERVABILITY_FOUNDATION.md` | Same | Milestone record | `docs/architecture/10_OBSERVABILITY.md` | Preserved |
| `docs/architecture/platform-v2/MR-007J_MULTI_SITE_PRODUCTION_READINESS.md` | Same | Milestone record | `docs/architecture/12_VALIDATION_AND_CERTIFICATION.md` | Preserved |
| `docs/architecture/platform-v2/MR-007_IMPLEMENTATION_BLUEPRINT.md` | Same | Milestone plan | `docs/architecture/README.md` | Preserved |
| `docs/architecture/platform-v2/MR-012_MULTI_SITE_FINAL_RECONCILIATION.md` | Same | Accepted reconciliation | `docs/architecture/platform-v2/MR-016_FINAL_ACCEPTANCE.md` | Preserved |
| `docs/architecture/platform-v2/MR-016_FINAL_ACCEPTANCE.md` | Same | Formal acceptance | Self | Preserved |
| `docs/architecture/platform-v2/NAMING_AND_TAGGING_STANDARD.md` | Same | Standard | Self | Preserved |
| `docs/architecture/platform-v2/REPOSITORY_LAYOUT.md` | Same | Historical target layout | `docs/architecture/REPOSITORY_STRUCTURE.md` | Preserved |
| `docs/architecture/platform-v2/STATE_AND_PROVIDER_STRATEGY.md` | Same | Terraform reference | `docs/architecture/11_DEPLOYMENT_ARCHITECTURE.md` | Preserved |
| `docs/archive/README.md` | Same | Archive index | Self | Preserved |
| `docs/archive/implementation-packages/MR-009D3C_INSTALL.md` | Same | Archived package | `docs/archive/README.md` | Preserved |
| `docs/archive/implementation-packages/MR-012_INSTALL.md` | Same | Archived package | `docs/archive/README.md` | Preserved |
| `docs/archive/implementation-packages/MR-013_INSTALL.md` | Same | Archived package | `docs/archive/README.md` | Preserved |
| `docs/archive/reviews/SHARED_FOUNDATION_REVIEW_MANIFEST.md` | Same | Archived review | `docs/archive/README.md` | Preserved |
| `docs/certification/MR-014_MULTI_SITE_CERTIFICATION.md` | Same | Formal certification | Self | Preserved intact |
| `docs/certification/MS-024A_PRE_PRODUCTION_READINESS_CERTIFICATION.md` | Same | Formal certification | Self | Preserved intact |
| `docs/engineering/CODEX_TASK_TEMPLATE.md` | Same | Template | `docs/engineering/README.md` | Preserved |
| `docs/engineering/CODEX_WORKING_CONTEXT.md` | Same | Historical working context | `docs/engineering/MULTI_SITE_COMPLETION_PLAN.md` | Preserved with completion notice |
| `docs/engineering/MULTI_SITE_COMPLETION_PLAN.md` | Same | Completion record | Self | Preserved |
| `docs/engineering/VALIDATION_CONTRACT.md` | Same | Active contract | Self | Preserved |
| `docs/engineering/ai-assisted-development/AI_ENGINEERING_PLAYBOOK.md` | Same | Engineering playbook | Self | Preserved |
| `docs/engineering/ai-assisted-development/ARR_TEMPLATE.md` | Same | Template | Playbook | Preserved |
| `docs/engineering/ai-assisted-development/EDS_TEMPLATE.md` | Same | Template | Playbook | Preserved |
| `docs/engineering/ai-assisted-development/ORR_TEMPLATE.md` | Same | Template | Playbook | Preserved |
| `docs/engineering/ai-assisted-development/README.md` | Same | Engineering index | Self | Preserved |
| `docs/engineering/ai-assisted-development/REVIEW_DECISION_RECORD_TEMPLATE.md` | Same | Template | Playbook | Preserved |
| `docs/engineering/slices/MR-012_OPERATIONAL_READINESS_AND_FINAL_RECONCILIATION.md` | Same | Delivery record | `docs/engineering/MULTI_SITE_COMPLETION_PLAN.md` | Preserved |
| `docs/engineering/slices/MR-013_EXPLICIT_WORKFLOW_STATE_MACHINE.md` | Same | Delivery record | Decision record | Preserved |
| `docs/engineering/slices/MR-014A_CONFIGURATION_PROFILE_COMPOSITION.md` | Same | Delivery record | Readiness profiles | Preserved |
| `docs/engineering/slices/MR-014_CONTROLLED_CHAOS_AND_FAILURE_VALIDATION.md` | Same | Delivery record | MR-014 certification | Preserved |
| `docs/engineering/slices/MR-014_END_TO_END_CHAOS_AND_FAILURE_CERTIFICATION.md` | Same | Delivery record | MR-014 certification | Preserved |
| `docs/engineering/slices/MR-015_MULTI_SITE_CLOSEOUT.md` | Same | Delivery record | Completion record | Preserved |
| `docs/engineering/slices/MR-016_MULTI_SITE_OPERATIONS_AND_ARCHITECTURE.md` | Same | Delivery record | Final acceptance | Preserved |
| `docs/history/PROJECT_BUILD_LOG.md` | Same | Historical chronology | `docs/history/README.md` | Preserved |
| `docs/lessons-learned.md` | Same | Historical lessons | `docs/history/README.md` | Preserved |
| `docs/operations/platform-v2/INCIDENT_EVIDENCE_COLLECTION_RUNBOOK.md` | Same | Active runbook | `docs/operations/incident-response/README.md` | Preserved |
| `docs/operations/platform-v2/MR-009D3C_GLOBAL_API_EDGE.md` | Same | Historical deployment record | Topology publication | Preserved |
| `docs/operations/platform-v2/MR-010B/VALIDATION_PLAN.md` | Same | Validation record | DR validation index | Preserved |
| `docs/operations/platform-v2/MR-010C/VALIDATION_PLAN.md` | Same | Validation record | DR validation index | Preserved |
| `docs/operations/platform-v2/MR-010D/VALIDATION_PLAN.md` | Same | Validation record | DR validation index | Preserved |
| `docs/operations/platform-v2/MR-010E/VALIDATION_PLAN.md` | Same | Validation record | Queue and DLQ guide | Preserved |
| `docs/operations/platform-v2/MR-010F/VALIDATION_PLAN.md` | Same | Validation record | DR validation index | Preserved |
| `docs/operations/platform-v2/MR-010G/ACCEPTANCE_REVIEW.md` | Same | Acceptance record | MR-014 certification | Preserved |
| `docs/operations/platform-v2/MR-014/CONTROLLED_CHAOS_RUNBOOK.md` | Same | Active controlled runbook | Self | Preserved |
| `docs/operations/platform-v2/MR-014/END_TO_END_CHAOS_CERTIFICATION_RUNBOOK.md` | Same | Active certification runbook | Self | Preserved |
| `docs/operations/platform-v2/MR-014A/CONFIGURATION_PROFILE_RUNBOOK.md` | Same | Active runbook | Self | Preserved |
| `docs/operations/platform-v2/MULTI_SITE_DEPLOYMENT_RUNBOOK.md` | Same | Active runbook | Self | Preserved |
| `docs/operations/platform-v2/MULTI_SITE_OPERATIONS_RUNBOOK.md` | Same | Active runbook | Self | Preserved |
| `docs/operations/platform-v2/QUEUE_BACKLOG_AND_DLQ_RUNBOOK.md` | Same | Active runbook | Self | Preserved |
| `docs/operations/platform-v2/REGIONAL_ISOLATION_AND_RECOVERY_RUNBOOK.md` | Same | Active runbook | Self | Preserved |
| `docs/operations/production/INCIDENT_RESPONSE_AND_REVIEW.md` | Same | Active operating procedure | Self | Preserved |
| `docs/operations/production/PRODUCTION_OPERATING_MODEL.md` | Same | Active operating model | Self | Preserved |
| `docs/operations/production/README.md` | Same | Active index | Self | Preserved |
| `docs/operations/production/SERVICE_OBJECTIVES_AND_KPIS.md` | Same | Active KPI reference | Self | Preserved |
| `docs/reference/REPOSITORY_STRUCTURE.md` | Same | Active redirect reference | `docs/architecture/REPOSITORY_STRUCTURE.md` | Preserved |
| `docs/reference/TOOLING_TAXONOMY.md` | Same | Active redirect reference | `docs/architecture/TOOLING_TAXONOMY.md` | Preserved |
| `docs/runbooks/OUTBOX_OPERATIONS.md` | Same | Active runbook | Self | Preserved |
| `portfolio/EXECUTIVE_SUMMARY.md` | Same | Portfolio publication | `portfolio/README.md` | Preserved |
| `portfolio/LEADERSHIP_CASE_STUDY.md` | Same | Portfolio publication | `portfolio/README.md` | Preserved |
| `portfolio/README.md` | Same | Portfolio index | Self | Preserved |
| `portfolio/VIDEO_WALKTHROUGH_TALKING_POINTS.md` | Same | Portfolio script | `portfolio/README.md` | Preserved |

### Merge

**Audience:** architects and maintainers.
**Purpose:** preserve strong source material whose current narrative now lives in a concept publication.
**Rationale:** the source remains available for traceability; its durable explanation was consolidated to avoid parallel architecture narratives.

| Current path | Proposed path | Status | Canonical destination | Unique content |
|---|---|---|---|---|
| `docs/architecture/platform-v2/PLATFORM_V2_ARCHITECTURE.md` | Same | Retained source after merge | `docs/architecture/02_PLATFORM_OVERVIEW.md` through `12_VALIDATION_AND_CERTIFICATION.md` | Preserved in source and canonical set |

### Redirect

**Audience:** readers following established links.
**Purpose:** preserve compatibility after executive consolidation.
**Rationale:** these paths were introduced or referenced during Phase 1 and may be bookmarked.

| Current path | Proposed path | Status | Canonical destination | Unique content |
|---|---|---|---|---|
| `docs/executive/ARCHITECTURE_GUIDE.md` | Same | Redirect | `docs/architecture/README.md` | Preserved in canonical set |
| `docs/executive/ARCHITECTURE_NARRATIVE.md` | Same | Redirect | `docs/executive/EXECUTIVE_SUMMARY.md` | Preserved in canonical set |
| `docs/executive/IMPLEMENTATION_HIGHLIGHTS.md` | Same | Redirect | `docs/executive/SYSTEM_CAPABILITIES.md` | Preserved in canonical set |
| `docs/executive/OPERATIONS_OVERVIEW.md` | Same | Redirect | `docs/executive/OPERATIONAL_READINESS.md` | Preserved in canonical set |
| `docs/executive/PLATFORM_ARCHITECTURE.md` | Same | Redirect | `docs/architecture/01_EXECUTIVE_OVERVIEW.md` | Preserved in canonical set |
| `docs/executive/RESILIENCE_OVERVIEW.md` | Same | Redirect | `docs/architecture/09_DISASTER_RECOVERY.md` | Preserved in canonical set |

### Archive

**Audience:** maintainers and auditors.
**Purpose:** identify approved historical runtime reports whose current guidance and final evidence exist elsewhere.
**Rationale:** these intermediate MR-009D records predate the completed MR-014 certification. They remain in place until the explicit archive script is separately approved and run.

| Current path | Proposed path | Status | Canonical destination | Unique content |
|---|---|---|---|---|
| `docs/operations/platform-v2/MR-009D_DEPLOYMENT_REPORT.md` | `docs/archive/operations/MR-009D_DEPLOYMENT_REPORT.md` | Archive candidate; not moved | Final acceptance and MR-014 certification | Preserved in source |
| `docs/operations/platform-v2/MR-009D_RUNTIME_DISCOVERY_REPORT.md` | `docs/archive/operations/MR-009D_RUNTIME_DISCOVERY_REPORT.md` | Archive candidate; not moved | Final acceptance and MR-014 certification | Preserved in source |
| `docs/operations/platform-v2/MR-009D_RUNTIME_EVIDENCE_REPORT.md` | `docs/archive/operations/MR-009D_RUNTIME_EVIDENCE_REPORT.md` | Archive candidate; not moved | MR-014 certification | Preserved in source |
| `docs/operations/platform-v2/MR-009D_RUNTIME_VALIDATION_PLAN.md` | `docs/archive/operations/MR-009D_RUNTIME_VALIDATION_PLAN.md` | Archive candidate; not moved | DR validation and MR-014 runbooks | Preserved in source |
| `docs/operations/platform-v2/MR-009D4_RUNTIME_VALIDATION_PLAN.md` | `docs/archive/operations/MR-009D4_RUNTIME_VALIDATION_PLAN.md` | Archive candidate; not moved | Regional isolation and MR-014 runbooks | Preserved in source |

### Draft

**Audience:** maintainers.
**Purpose:** record non-authoritative Markdown drafts.
**Rationale:** no Markdown draft currently exists. `docs/drafts/mr-004c/outbox_publisher.tf` is a Terraform draft, is not part of this Markdown inventory, and remains non-authoritative.

No Markdown files are classified Draft.
