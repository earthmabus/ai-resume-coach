# MR-007H — Edge Security Foundation

## Decision

Platform V2 retains API Gateway HTTP APIs because they provide the required
JWT authorization, CORS, automatic deployment, access logging, and throttling
at a lower price than REST APIs.

AWS WAF cannot be associated directly with API Gateway HTTP API stages. Direct
API Gateway WAF integration is available for REST APIs, not HTTP APIs.

MR-007H therefore does not claim that WAF protects the Regional HTTP APIs.

## Controls introduced

### Shared Cognito protection

A cost-gated Regional AWS WAF web ACL can be associated with the shared Cognito
user pool in `us-east-1`.

The baseline contains:

- AWS Managed Rules Common Rule Set;
- AWS Managed Rules Known Bad Inputs Rule Set;
- AWS Managed Rules Amazon IP Reputation List;
- a per-IP rate-based block rule.

### Privacy-aware logging

Optional WAF logging:

- is disabled by default;
- uses a seven-day default retention period;
- records only blocked or counted requests;
- redacts the `Authorization` header.

### Regional HTTP API hardening

The two HTTP APIs continue to rely on:

- Cognito JWT authorization for application routes;
- public-only health routes;
- symmetric stage-level burst and sustained-rate throttling;
- structured access logs;
- TLS-protected Regional custom domains.

### DDoS baseline

AWS Shield Standard is the documented baseline. Shield Advanced is excluded
because its recurring cost is disproportionate for a portfolio workload.

## Cost controls

```hcl
enable_cognito_waf         = false
enable_cognito_waf_logging = false
```

The WAF web ACL, association, and logging resources are created only when
explicitly enabled.

## Deferred options

If direct WAF inspection of API requests becomes mandatory, evaluate one of:

1. migrate the API surface from HTTP APIs to REST APIs;
2. introduce an ingress service that AWS WAF supports;
3. redesign global routing around a WAF-capable edge layer.

That decision must include cost, active-active routing, latency, operational
complexity, and migration impact.
