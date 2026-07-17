# MR-007J — Multi-Site Production Readiness

## Problem

Platform V2 can run in two active Regions, but production deployment requires explicit controls for regional routing, staged rollout, readiness validation, and rollback.

## Goals

- Allow either Region to be removed from global routing.
- Prevent configuration with no routable Region.
- Expose a concise production-readiness contract.
- Standardize a west-first, region-by-region deployment sequence.
- Keep operational documentation out of the deployment critical path.

## Decisions

- Route 53 records are controlled independently through `site_routing_enabled`.
- Regional infrastructure remains deployed when a site is isolated; only its global DNS record is removed.
- Production enforcement is opt-in through `production_readiness_enforced`.
- Required controls are global routing, Route 53 health checks, Cognito WAF, structured logging, dashboard, alarms, and synthetics.
- Rollback occurs one Region at a time. Data correction uses compensating actions rather than Terraform rollback.

## Deployment contract

1. Deploy west.
2. Validate west health, deployment ID, alarms, and synthetics.
3. Deploy east.
4. Validate east.
5. Enable and validate global routing.

## Non-goals

This MR does not automate failure injection, DLQ replay, data repair, incident escalation, or application migration.
