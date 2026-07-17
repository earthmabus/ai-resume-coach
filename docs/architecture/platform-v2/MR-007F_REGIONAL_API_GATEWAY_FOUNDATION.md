# MR-007F — Regional API Gateway Foundation

## Goal

Expose each active regional application site through an independently
deployable, authenticated HTTP API while keeping global traffic routing
deferred.

## Cost-conscious choices

- API Gateway HTTP APIs are used instead of REST APIs.
- The `$default` stage uses automatic deployment.
- Detailed per-route metrics are disabled by default.
- Access-log retention is 14 days.
- Default throttling is conservative: 10 requests/second with a burst of 25.
- No custom domains, private integrations, provisioned capacity, or API cache
  are introduced in this slice.

## Public routes

- `GET /health`
- `GET /health/live`
- `GET /health/ready`

These routes are intentionally unauthenticated so infrastructure and future
edge-routing health checks can evaluate each Region.

## Protected routes

- `GET /job-matching`
- `POST /job-matching`
- `DELETE /job-matching/{matchId}`
- `POST /resume-analysis`
- `POST /resume-tailoring`
- `GET /profile`
- `PUT /profile`

Protected routes use an API Gateway JWT authorizer backed by the shared Cognito
user-pool issuer and application-client audience.

## Integration

All routes use a Lambda proxy integration with payload format version 2.0.
API Gateway receives explicit permission to invoke only the regional API
Lambda.

## Logging

Each Region receives a dedicated API access-log group with structured JSON.
Detailed metrics remain disabled to avoid unnecessary recurring cost.

## Deferred

- CloudFront and Route 53 global routing
- regional origin failover
- custom API domains
- AWS WAF
- Shield Advanced
- tracing and synthetic monitoring
- S3 cross-Region replication
