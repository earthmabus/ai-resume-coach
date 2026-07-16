# Architecture Decisions

## P2-001 — Clean rebuild
Destroy and rebuild rather than preserve legacy Terraform addresses because there is one user, backups exist, and long-term code quality is more valuable.

## P2-002 — Symmetric module
Both active sites use one regional module.

## P2-003 — Shared Cognito
One user pool serves both APIs for MR-007.

## P2-004 — Shared edge
One frontend, CloudFront distribution, certificate, and custom domain.

## P2-005 — Independent data in MR-007
Separate regional tables and buckets temporarily validate deployment before replication.

## P2-006 — Local async pipeline
Each Region owns its queue, DLQ, publisher, and worker.

## P2-007 — One state initially
One environment state is appropriate for one operator and one workflow.

## P2-008 — East is initial frontend target
Traffic management is deferred.

## P2-009 — Preserve reliability patterns
Idempotency, outbox, replay, provenance, and optimistic concurrency remain mandatory.

## P2-010 — Full Region names in data
Use full AWS Region names in application records; abbreviations are infrastructure-only.
