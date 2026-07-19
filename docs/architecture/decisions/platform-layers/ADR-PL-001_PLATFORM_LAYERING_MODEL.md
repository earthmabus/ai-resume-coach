# ADR-PL-001: Platform Layering Model

Status: Proposed

## Context

The two-region baseline is deployed and validated, but shared, regional, global-ingress, and production-only concerns are currently discussed as individual resources. That makes ownership and deployment sequencing harder to reason about.

## Decision

Adopt four explicit architecture layers:

- **Shared Foundation**: identity, multi-region system of record, shared notification capability, common topology contracts.
- **Regional Application Sites**: API Gateway, Lambda, SQS/DLQ, regional S3, regional health and runtime identity.
- **Global Traffic Management**: regional API custom domains, certificates, DNS records, health checks, and routing policy.
- **Production Operations Overlay**: WAF, dashboards, alarms, synthetics, tracing, and enforced production-readiness controls.

Dependencies flow downward only. Regional sites consume shared-foundation outputs. Global traffic management consumes regional-site outputs. The production overlay observes and protects all lower layers without becoming a prerequisite for development deployments.

## Consequences

- Baseline deployments remain low-cost and directly testable by regional endpoint.
- Global routing can be implemented and rolled back independently.
- Production controls remain explicit, cost-gated overlays.
- Terraform module and state boundaries become visible architectural contracts.
