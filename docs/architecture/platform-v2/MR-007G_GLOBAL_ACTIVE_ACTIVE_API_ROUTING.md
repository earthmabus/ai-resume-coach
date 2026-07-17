# MR-007G — Global Active-Active API Routing

## Goal

Give clients one stable API hostname while allowing Route 53 to select between
the independently deployable APIs in `us-east-1` and `us-west-2`.

## Architecture

Each active Region receives the same Regional API Gateway custom domain. Route
53 publishes two latency alias records for the shared hostname:

- `us-east-1` → east Regional API custom domain
- `us-west-2` → west Regional API custom domain

This preserves active-active request routing. It intentionally does not use a
CloudFront origin group, because an origin group establishes primary/secondary
failover rather than latency-based active-active routing.

## Cost guardrails

Global API routing is disabled by default:

```hcl
enable_global_api_routing = false
```

Route 53 endpoint health checks are controlled separately and are also disabled
by default:

```hcl
enable_route53_api_health_checks = false
```

This allows the infrastructure contract to be validated without silently
creating recurring Route 53 resources.

## Deployment prerequisites

When enabling the feature, provide:

- an existing public hosted-zone ID;
- one validated ACM certificate ARN in `us-east-1`;
- one validated ACM certificate ARN in `us-west-2`;
- the common API hostname covered by both certificates.

Certificate creation and DNS validation are intentionally external to this
slice because the user's domain is managed outside this project account.

## Health checks

When enabled, Route 53 probes:

```text
HTTPS /health/ready
```

The health checks use 30-second intervals, no latency measurements, and a
configurable failure threshold. They are associated with the corresponding
latency records so DNS responses can omit an unhealthy Region.

## Deferred

- frontend CloudFront distribution and S3 origin failover;
- WAF;
- Shield Advanced;
- alarms and operational dashboards;
- automatic ACM certificate issuance;
- migration cutover from Platform V1.
