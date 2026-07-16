# Module Specification

## Root composition

Root Terraform owns providers, shared variables, package archive data sources, shared/global resources, regional module instantiation, cross-module wiring, and public outputs. It must not contain regional Lambda, queue, table, or alarm implementations.

## `regional_application` module

### Purpose

Deploy one complete regional application site.

### Inputs

- project and environment;
- Region and explicit region code;
- application version and deployment ID;
- logging and AI provider settings;
- Cognito issuer and client ID;
- API, worker, publisher, and layer artifact paths and hashes;
- optional regional alert email.

### Owned resources

**API:** HTTP API, JWT authorizer, public/authenticated routes, stage, Lambda integration, invoke permission.

**Compute:** API Lambda, worker, outbox publisher, PDF layer, SQS event mapping, publisher schedule.

**Messaging:** processing queue, DLQ, redrive policy, redrive allow policy.

**Data for MR-007:** regional DynamoDB table and regional documents bucket with encryption, versioning, public access block, and CORS.

**IAM:** application role, publisher role, least-privilege regional policies, logging attachments.

**Observability:** dashboards, alarms, log retention, regional SNS operational topic.

### Outputs

Region, API endpoint, health URL, table/bucket/queue identities, Lambda names, dashboard name, and alert topic ARN.

### Prohibited ownership

Cognito, CloudFront, ACM, Route 53, frontend bucket, registration notification, GitHub OIDC roles, and Terraform backend.

## `global_edge` module

Owns frontend bucket, CloudFront, OAC, response-header/cache policies, bucket policy, frontend objects, generated `config.js`, custom-domain alias, and certificate validation wiring.

During MR-007, `config.js` points to east. The module does not balance API traffic.

## Shared identity

Cognito and registration notification may remain at root until a second identity deployment is justified.

## Future `multi_region_data` module

MR-008 may move DynamoDB ownership into a dedicated module for replicas, witness, backups, deletion protection, and outputs consumed by the regional modules.
