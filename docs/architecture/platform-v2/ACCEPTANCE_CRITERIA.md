# Platform V2 Multi-Site Acceptance Criteria

Status: **Accepted July 22, 2026**

## Architecture

- [x] East and west use the same regional module.
- [x] Root Terraform composes rather than duplicates regional compute.
- [x] Shared and global resources are created once.
- [x] Provider aliases are explicit.
- [x] Naming is symmetric and region-qualified.
- [x] DynamoDB MRSC uses active replicas in east and west with the configured witness responsibility in `us-east-2`.

## Build and test

- [x] Python tests pass.
- [x] Package and validation-tool tests pass.
- [x] Terraform formatting, validation, and tests pass.
- [x] Routing mutation plans are constrained to the intended Route 53 records.
- [x] Runtime Terraform inputs are aligned with the deployed Lambda configuration.

## Regional execution

- [x] Each API uses its regional document bucket and processing path.
- [x] Work is dispatched to the deterministic owner-region queue.
- [x] Each worker consumes only its regional queue.
- [x] Ownership and state transitions prevent incorrect regional processing.
- [x] Duplicate API and transport delivery remains idempotent.

## Shared services

- [x] One Cognito user pool serves both APIs.
- [x] One registration-notification path exists.
- [x] One frontend and CloudFront distribution exist.
- [x] One MRSC DynamoDB system of record serves both active sites.
- [x] Route 53 exposes both active APIs through one global hostname.

## Runtime certification

- [x] East health reports `us-east-1`.
- [x] West health reports `us-west-2`.
- [x] Both sites report the certified deployment ID.
- [x] Authentication works through global and regional APIs.
- [x] End-to-end resume processing works through the multi-site path.
- [x] East isolation and restoration pass.
- [x] West isolation and restoration pass.
- [x] Terraform rejects disabling both sites.
- [x] Worker interruption retains backlog and restoration completes it.
- [x] Final queue drain and post-recovery reconciliation pass.

## Operations

- [x] Regional readiness, queue, DLQ, mapping, publisher, worker, and MRSC preflight checks exist.
- [x] Mutating certification requires explicit authorization flags.
- [x] Routing and worker mutations have exit-trap restoration.
- [x] A consolidated operations runbook exists.
- [x] Sanitized certification evidence is preserved.
- [ ] Permanent dashboards, alarms, synthetics, and Cognito WAF are enabled. This is explicitly deferred to production hardening and does not block multi-site acceptance.

## Documentation

- [x] Final architecture is committed.
- [x] Implementation pivots are recorded.
- [x] Certification and accepted limitations are recorded.
- [x] Final architecture posters are regenerated.
- [x] Architecture and operational acceptance is recorded.
