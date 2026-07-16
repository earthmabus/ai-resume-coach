# AI Resume Coach — Platform V2 Architecture Design

This package is the authoritative design baseline for the clean infrastructure rebuild that precedes the multi-site active-active implementation.

## Purpose

Platform V2 replaces the current single-region, root-heavy Terraform layout with a symmetric regional architecture:

- shared global and edge capabilities;
- one reusable regional application module;
- identical active application sites in `us-east-1` and `us-west-2`;
- a clean path to DynamoDB multi-region strong consistency;
- explicit operational, deployment, and failure boundaries.

## Document map

1. `PLATFORM_V2_ARCHITECTURE.md`
2. `MODULE_SPECIFICATION.md`
3. `REPOSITORY_LAYOUT.md`
4. `STATE_AND_PROVIDER_STRATEGY.md`
5. `NAMING_AND_TAGGING_STANDARD.md`
6. `DATA_AND_REGION_BOUNDARIES.md`
7. `CI_CD_AND_RELEASE_MODEL.md`
8. `DEPLOYMENT_AND_REBUILD_RUNBOOK.md`
9. `FAILURE_ROLLBACK_AND_RECOVERY.md`
10. `ARCHITECTURE_DECISIONS.md`
11. `MR_007_IMPLEMENTATION_BLUEPRINT.md`
12. `ACCEPTANCE_CRITERIA.md`
13. `diagrams/`

**Status: Approved for implementation**
