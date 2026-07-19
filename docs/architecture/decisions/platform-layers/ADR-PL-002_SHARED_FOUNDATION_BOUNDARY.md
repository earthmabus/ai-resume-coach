# ADR-PL-002: Shared Foundation Boundary

Status: Proposed

## Decision

The Shared Foundation owns resources that must be singular or logically shared across active sites:

- Cognito user pool, client, domain, and validation group.
- Registration-notification SNS topic, Lambda, IAM, logs, and Cognito invocation permission.
- DynamoDB MRSC Resume Analysis system of record, including the us-west-2 strong-consistency replica and us-east-2 witness.
- Exported identity, notification, and data-topology contracts.

It does not own:

- Regional Lambda functions or queues.
- Regional document buckets.
- API Gateway endpoints.
- Route 53, API custom domains, or ACM certificates.
- WAF, dashboards, alarms, or synthetic monitoring.

## State and deployment rule

The first implementation is a structural refactor, not a resource replacement. Terraform `moved` blocks preserve the deployed resource identities while transferring ownership into `module.shared_foundation`.

Any plan showing destruction or replacement of Cognito or DynamoDB resources is a release blocker.
