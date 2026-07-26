# AI Resume Coach Documentation

> **Status:** Canonical
> **Audience:** All repository readers
> **Purpose:** Route each reader to the authoritative documentation for their goal
> **Owner:** Documentation Maintainers
> **Related documents:** [Document index](DOCUMENT_INDEX.md), [document mapping](DOCUMENT_MAPPING.md)
> **Reading time:** 5–10 minutes

This directory contains the current architecture, operations, engineering, certification, product, portfolio, and historical records for AI Resume Coach.

The documentation is organized around reader intent. Milestone identifiers remain in implementation and certification records where they provide traceability, but readers should use the current architecture and operations documents as their primary source of truth.

## Start Here

| I want to… | Begin with |
|---|---|
| Understand the platform in business terms | [Executive Summary](executive/EXECUTIVE_SUMMARY.md) |
| Understand the implemented system | [Architecture Publications](architecture/README.md) |
| See the multi-region design | [Multi-Site Architecture Diagram Portfolio](mvp2-disaster-recovery/README.md) |
| Understand a request from ingress through processing | [Request Lifecycle](architecture/06_REQUEST_LIFECYCLE.md) |
| Understand asynchronous work and ownership | [Processing Architecture](architecture/08_PROCESSING_ARCHITECTURE.md) |
| Deploy or rebuild the platform | [Deployment](operations/deployment/README.md) |
| Operate the active-active platform | [Operations Portal](operations/README.md) |
| Respond to a regional incident | [Regional Isolation and Recovery Runbook](operations/platform-v2/REGIONAL_ISOLATION_AND_RECOVERY_RUNBOOK.md) |
| Understand production operations | [Production Operations](operations/production/README.md) |
| Review runtime certification | [MR-014 Multi-Site Certification](certification/MR-014_MULTI_SITE_CERTIFICATION.md) |
| Review readiness profiles | [MS-024A Production Readiness Profiles](architecture/platform-resilience/MS-024A_PRODUCTION_READINESS_PROFILES.md) |
| Contribute code or infrastructure | [Repository Guidance](../AGENTS.md) and [Validation Contract](engineering/VALIDATION_CONTRACT.md) |
| Understand repository organization | [Repository Structure](architecture/REPOSITORY_STRUCTURE.md) and [Document Index](DOCUMENT_INDEX.md) |
| Review project chronology | [Project Build Log](history/PROJECT_BUILD_LOG.md) |

## Documentation Authority

When documents appear to overlap, use this order of authority:

1. Executable application tests and Terraform contract tests
2. Supported validation and operations tooling
3. Current architecture and operations documentation
4. Formal certification records
5. Engineering delivery records
6. Historical and archived material

A conflict between executable behavior and documentation should be reported and resolved rather than silently interpreted.

## Executive and Portfolio Reading

The executive layer explains why the platform exists, what it provides, and why its architecture matters.

Canonical executive documents:

- [Executive Documentation](executive/README.md)
- [Executive Summary](executive/EXECUTIVE_SUMMARY.md)
- [Platform Overview](executive/PLATFORM_OVERVIEW.md)
- [System Capabilities](executive/SYSTEM_CAPABILITIES.md)
- [Operational Readiness](executive/OPERATIONAL_READINESS.md)
- [Product Roadmap](executive/PRODUCT_ROADMAP.md)
- [Glossary](executive/GLOSSARY.md)

The repository also contains portfolio-oriented materials:

- [Director Portfolio](../portfolio/README.md)
- [Multi-Site Architecture Diagram Portfolio](mvp2-disaster-recovery/README.md)
- [Video Walkthrough Talking Points](../portfolio/VIDEO_WALKTHROUGH_TALKING_POINTS.md)

Older executive architecture, operations, highlights, and resilience paths remain as compatibility redirects.

## Architecture

### Current System Architecture

- [Architecture Publications](architecture/README.md)
- [Architecture Document Index](architecture/DOCUMENT_INDEX.md)
- [Executive Architecture Overview](architecture/01_EXECUTIVE_OVERVIEW.md)
- [Platform Overview](architecture/02_PLATFORM_OVERVIEW.md)
- [Logical Architecture](architecture/03_LOGICAL_ARCHITECTURE.md)
- [Physical Architecture](architecture/04_PHYSICAL_ARCHITECTURE.md)
- [Security Architecture](architecture/05_SECURITY_ARCHITECTURE.md)
- [Request Lifecycle](architecture/06_REQUEST_LIFECYCLE.md)
- [Data Architecture](architecture/07_DATA_ARCHITECTURE.md)
- [Processing Architecture](architecture/08_PROCESSING_ARCHITECTURE.md)
- [Disaster Recovery](architecture/09_DISASTER_RECOVERY.md)
- [Observability](architecture/10_OBSERVABILITY.md)
- [Deployment Architecture](architecture/11_DEPLOYMENT_ARCHITECTURE.md)
- [Validation and Certification](architecture/12_VALIDATION_AND_CERTIFICATION.md)
- [Operational Runbook](architecture/13_OPERATIONAL_RUNBOOK.md)
- [Architectural Decisions](architecture/14_ARCHITECTURAL_DECISIONS.md)
- [Repository Structure](architecture/REPOSITORY_STRUCTURE.md)
- [Operational Tooling Taxonomy](architecture/TOOLING_TAXONOMY.md)

### Platform V2 and Multi-Site Architecture

The platform-v2 directory preserves the detailed implementation and acceptance record. The numbered architecture set is the current primary narrative.

- [Platform V2 Architecture](architecture/platform-v2/PLATFORM_V2_ARCHITECTURE.md)
- [Implementation Blueprint](architecture/platform-v2/MR-007_IMPLEMENTATION_BLUEPRINT.md)
- [Data and Region Boundaries](architecture/platform-v2/DATA_AND_REGION_BOUNDARIES.md)
- [State and Provider Strategy](architecture/platform-v2/STATE_AND_PROVIDER_STRATEGY.md)
- [Failure, Rollback, and Recovery](architecture/platform-v2/FAILURE_ROLLBACK_AND_RECOVERY.md)
- [CI/CD and Release Model](architecture/platform-v2/CI_CD_AND_RELEASE_MODEL.md)
- [Architecture Decisions](architecture/platform-v2/ARCHITECTURE_DECISIONS.md)
- [Acceptance Criteria](architecture/platform-v2/ACCEPTANCE_CRITERIA.md)
- [Final Acceptance](architecture/platform-v2/MR-016_FINAL_ACCEPTANCE.md)

Detailed milestone records remain in the same directory for implementation traceability.

### Durable Architecture Decisions

- [Architecture Decision Records](architecture/decisions/)
- [Platform Layering Decisions](architecture/decisions/platform-layers/README.md)
- [Multi-Site Topology Decision](architecture/decisions/MS-001_MULTI_SITE_TOPOLOGY.md)
- [Single-Table Decision](architecture/decisions/MS-002_SINGLE_TABLE_FOR_NOW.md)
- [Work Ownership and Placement](architecture/decisions/MS-005_WORK_OWNERSHIP_AND_PLACEMENT.md)
- [Correlation and Traceability](architecture/decisions/MS-007_CORRELATION_AND_TRACEABILITY.md)
- [Regional Health Classification](architecture/decisions/MS-008_REGIONAL_HEALTH_CLASSIFICATION.md)

## Disaster Recovery and Resilience

The consolidated publication home contains concept documentation and the final architecture poster series in editable Graphviz, SVG, and PNG formats:

- [Diagram Portfolio Guide](mvp2-disaster-recovery/README.md)
- [Topology and Global Routing](mvp2-disaster-recovery/architecture/TOPOLOGY_AND_ROUTING.md)
- [Identity Recovery](mvp2-disaster-recovery/architecture/IDENTITY_RECOVERY.md)
- [Data Consistency](mvp2-disaster-recovery/architecture/DATA_CONSISTENCY.md)
- [Processing Ownership](mvp2-disaster-recovery/architecture/PROCESSING_OWNERSHIP.md)
- [Regional Recovery](mvp2-disaster-recovery/operations/REGIONAL_RECOVERY.md)
- [Validation](mvp2-disaster-recovery/validation/README.md)
- [Readiness and Certification](mvp2-disaster-recovery/certification/README.md)
- [Diagram Catalog](mvp2-disaster-recovery/diagrams/README.md)
- Executive multi-site architecture
- C4 system context
- C4 container architecture
- Runtime request and workflow
- Failure recovery and certification
- Data ownership and consistency
- Architecture evolution timeline

The detailed resilience implementation record currently remains under
[architecture/platform-resilience/](architecture/platform-resilience/):

- Baseline assessment
- Global API routing
- Identity recovery
- Document replication
- Processing ownership
- Disaster recovery validation
- Production observability
- Production readiness certification
- Readiness profiles

The milestone records remain at their established paths for traceability and are mapped in [DOCUMENT_MAPPING.md](DOCUMENT_MAPPING.md).

## Operations

[Operations Portal](operations/README.md) is the operator entry point.

### Multi-Site Operations

- [Multi-Site Operations Runbook](operations/platform-v2/MULTI_SITE_OPERATIONS_RUNBOOK.md)
- [Multi-Site Deployment Runbook](operations/platform-v2/MULTI_SITE_DEPLOYMENT_RUNBOOK.md)
- [Regional Isolation and Recovery](operations/platform-v2/REGIONAL_ISOLATION_AND_RECOVERY_RUNBOOK.md)
- [Queue Backlog and DLQ Operations](operations/platform-v2/QUEUE_BACKLOG_AND_DLQ_RUNBOOK.md)
- [Incident Evidence Collection](operations/platform-v2/INCIDENT_EVIDENCE_COLLECTION_RUNBOOK.md)
- [Controlled Chaos Runbook](operations/platform-v2/MR-014/CONTROLLED_CHAOS_RUNBOOK.md)
- [End-to-End Chaos Certification Runbook](operations/platform-v2/MR-014/END_TO_END_CHAOS_CERTIFICATION_RUNBOOK.md)

Runtime validation plans and evidence reports under `operations/platform-v2/` are retained for traceability. They are not substitutes for the current operator runbooks.

### Production Operations

- [Production Operations](operations/production/README.md)
- [Production Operating Model](operations/production/PRODUCTION_OPERATING_MODEL.md)
- [Service Objectives and KPI Catalog](operations/production/SERVICE_OBJECTIVES_AND_KPIS.md)
- [Incident Response and Review](operations/production/INCIDENT_RESPONSE_AND_REVIEW.md)

### Additional Runbooks

- [Outbox Operations](runbooks/OUTBOX_OPERATIONS.md)

## Certification and Readiness

Formal evidence and conclusions live under `docs/certification/`.

- [Certification Records](certification/README.md)
- [MR-014 Multi-Site Certification](certification/MR-014_MULTI_SITE_CERTIFICATION.md)
- [MS-024A Pre-Production Readiness Certification](certification/MS-024A_PRE_PRODUCTION_READINESS_CERTIFICATION.md)

Certification proves a defined contract under recorded conditions. It does not replace continued monitoring, operations, or environment-specific production controls.

## Engineering

Engineering documentation explains how the platform was delivered and how changes should be validated.

- [Engineering Documentation](engineering/README.md)
- [Validation Contract](engineering/VALIDATION_CONTRACT.md)
- [Multi-Site Completion Record](engineering/MULTI_SITE_COMPLETION_PLAN.md)
- [AI-Assisted Engineering Playbook](engineering/ai-assisted-development/README.md)
- [AI Engineering Playbook](engineering/ai-assisted-development/AI_ENGINEERING_PLAYBOOK.md)
- [Implementation Slices](engineering/slices/)
- [Codex Task Template](engineering/CODEX_TASK_TEMPLATE.md)
- [Codex Working Context](engineering/CODEX_WORKING_CONTEXT.md)

Implementation slices are delivery records. Current runtime behavior should be confirmed against the current architecture, code, tests, Terraform, and operations tooling.

## Product Documentation

Product documentation describes the experiences, decisions, and roadmap that shape the user-facing platform.

Use [Product Documentation](product/README.md) for product decisions and requirements. Product documents describe user and business intent without redefining infrastructure architecture.

## History, Archive, and Drafts

### History

[Project history](history/) preserves chronology and lessons learned. It is not the authoritative description of current behavior.

### Archive

[Archived engineering material](archive/README.md) preserves superseded packages and reviews for traceability.

### Drafts

Content under `docs/drafts/` is not current architecture or supported infrastructure. Draft files must not be treated as deployable source unless explicitly promoted.

## Repository and Tooling Guidance

- [Repository Structure](architecture/REPOSITORY_STRUCTURE.md)
- [Operational Tooling Taxonomy](architecture/TOOLING_TAXONOMY.md)
- [Repository Guidance](../AGENTS.md)
- [Validation Contract](engineering/VALIDATION_CONTRACT.md)

At minimum, relevant changes should use focused validation followed by the repository's full validation contract.

## Documentation Maintenance Rules

When adding or changing documentation:

1. Place information in the directory owned by its audience and purpose.
2. Prefer links to an authoritative document over copying the same explanation.
3. Mark drafts, historical records, and archived documents clearly.
4. Keep milestone identifiers in implementation and certification records, not in generic operator entry points.
5. Update this portal when a new canonical document is introduced.
6. Do not remove an overlapping document until its unique content has been mapped to a replacement or archive location.
7. Report documentation and executable-contract conflicts explicitly.

## Modernization Record

The repository-wide modernization preserves `README.md` as the landing page and this file as the documentation portal. The canonical architecture, executive, disaster-recovery, operations, certification, engineering, product, reference, history, and archive entry points are active.

- [Complete Document Index](DOCUMENT_INDEX.md)
- [Per-File Document Mapping](DOCUMENT_MAPPING.md)
- [Migration Guide](MIGRATION_GUIDE.md)
