# Platform Layers Architecture Decision Package

Status: Proposed for review

This package separates the deployed platform into four explicit layers:

1. Shared Foundation
2. Regional Application Sites
3. Global Traffic Management
4. Production Operations Overlay

Review order:

- ADR-PL-001 Platform Layering Model
- ADR-PL-002 Shared Foundation Boundary
- ADR-PL-003 Global Ingress Boundary
- ADR-PL-004 Production Operations Overlay
- SHARED_FOUNDATION_CHANGE_PLAN.md
- REVIEW_CHECKLIST.md

No decision in this package enables global routing or paid production controls by default.
