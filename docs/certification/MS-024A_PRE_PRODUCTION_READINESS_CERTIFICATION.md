# MS-024A Profile-Aware Readiness Certification

## Decision

**PRE PRODUCTION CERTIFIED — generated 2026-07-26T16:29:50.610297+00:00.**

Profile: **Pre-Production** (`pre-production`)  
Profile ready: **YES**  
Production ready: **NO**  
Deployment ID: `f8c422ce9de4b9bdb55b530f39764e4c432a854f`

## Summary

- Checks: 17 passed, 4 warnings, 0 failed.
- Warnings are accepted profile exceptions; failed required controls block certification.
- This record is generated from Terraform outputs and live AWS control-plane validation.

## Category results

| Category | Status | Passed | Warnings | Failed |
|---|---:|---:|---:|---:|
| Architecture | PASS | 1/1 | 0 | 0 |
| Governance | WARN | 1/3 | 2 | 0 |
| Operations | WARN | 5/6 | 1 | 0 |
| Reliability | PASS | 8/8 | 0 | 0 |
| Security | WARN | 2/3 | 1 | 0 |

## Detailed checks

- **PASS — active_active_topology (Architecture):** Both approved active application sites are deployed. Evidence: `terraform-outputs.json`.
- **PASS — global_routing (Reliability):** Latency routing and Route 53 health checks are enabled. Evidence: `terraform-outputs.json`.
- **PASS — mrsc_data (Reliability):** DynamoDB MRSC matches the approved replicas and witness. Evidence: `terraform-outputs.json`.
- **PASS — document_continuity (Reliability):** Bidirectional document replication is enabled. Evidence: `terraform-outputs.json`.
- **PASS — processing_ownership (Reliability):** Persisted owner-region enforcement is fail-closed. Evidence: `terraform-outputs.json`.
- **PASS — identity_recovery (Reliability):** Warm-standby identity recovery is enabled with truthful reset-required boundaries. Evidence: `terraform-outputs.json`.
- **PASS — east_readiness (Reliability):** The east regional readiness endpoint passed. Evidence: `east-ready.json`.
- **PASS — west_readiness (Reliability):** The west regional readiness endpoint passed. Evidence: `west-ready.json`.
- **PASS — global_readiness (Reliability):** The global readiness endpoint passed. Evidence: `global-ready.json`.
- **PASS — observability_contract (Operations):** Dashboard, regional alarms, and synthetic monitoring are enabled. Evidence: `terraform-outputs.json`.
- **PASS — regional_alarms (Operations):** All 28 curated alarms exist (14 east, 14 west). Evidence: `east-alarms.json,west-alarms.json`.
- **WARN — alarm_notifications (Operations):** Alarm notification actions are not configured; this is accepted by the pre-production profile. Evidence: `terraform-outputs.json`.
- **PASS — global_canary (Operations):** ai-resume-coach-dev-g is running. Evidence: `global-canary.json`.
- **PASS — east_canary (Operations):** ai-resume-coach-dev-e is running. Evidence: `east-canary.json`.
- **PASS — west_canary (Operations):** ai-resume-coach-dev-w is running. Evidence: `west-canary.json`.
- **PASS — structured_logging (Security):** Structured logging and authorization-header redaction are enabled. Evidence: `terraform-outputs.json`.
- **PASS — data_protection (Security):** Document encryption and DynamoDB point-in-time recovery are enabled. Evidence: `terraform-outputs.json`.
- **WARN — cognito_waf (Security):** Cognito WAF is recommended but not required by the pre-production profile. Evidence: `terraform-outputs.json`.
- **WARN — readiness_enforcement (Governance):** Terraform production-readiness enforcement is disabled; this is accepted by the pre-production profile. Evidence: `terraform-outputs.json`.
- **WARN — terraform_readiness_gate (Governance):** Terraform production controls are not complete (cognito_waf); this is accepted by the pre-production profile. Evidence: `terraform-outputs.json`.
- **PASS — resilience_certification (Governance):** The durable MR-014 multi-site certification record exists. Evidence: `../../docs/certification/MR-014_MULTI_SITE_CERTIFICATION.md`.

## Accepted profile exceptions and warnings

- Alarm notification actions are not configured; this is accepted by the pre-production profile.
- Cognito WAF is recommended but not required by the pre-production profile.
- Terraform production-readiness enforcement is disabled; this is accepted by the pre-production profile.
- Terraform production controls are not complete (cognito_waf); this is accepted by the pre-production profile.

## Certified boundaries

- Certification applies only to the selected deployment profile.
- Bounded loss or isolation of either active application region.
- Warm-standby identity recovery requires password reset and does not preserve sessions.
- Processing ownership remains fail-closed; automatic reassignment and cross-region queue draining are not claimed.
- Synthetic monitoring covers public health endpoints only.

## Change control

Re-run MS-024A after changing the deployment profile or making material changes to routing, identity, persistence, processing ownership, observability, security controls, or readiness enforcement.
