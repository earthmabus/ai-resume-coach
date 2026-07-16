# MR-007 Implementation Blueprint

## Objective

Rebuild development as Platform V2 with two symmetric regional sites.

## Work packages

1. **Root composition:** providers, variables, site map, common tags, artifacts, module instances, outputs.
2. **Regional module:** API, compute, messaging, temporary data, IAM, monitoring, outputs.
3. **Global edge:** frontend, CloudFront, certificate wiring, Route 53, generated configuration.
4. **Shared identity:** Cognito, domain, client, registration notification, topic/subscription.
5. **Terraform tests:** provider wiring, naming uniqueness, local resource references, frontend east endpoint, no duplicate registration trigger.
6. **CI/CD:** build once, deploy both, Terraform tests, smoke-test both, preserve concurrency.
7. **Rebuild:** destroy V1, install V2, plan from clean state, apply, confirm subscriptions, re-register, test.
8. **Documentation:** update architecture and record actual pivots.

## Expected fresh-state plan

All managed actions should be additions. References to old root regional addresses indicate obsolete Terraform files remain.

## Exit criteria

Both health and version endpoints pass, deployment IDs match, workers and publishers pass, authentication works against both APIs, end-to-end processing succeeds in each Region, and Terraform returns no changes.
