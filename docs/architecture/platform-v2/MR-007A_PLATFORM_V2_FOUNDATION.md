# MR-007A — Platform V2 Foundation

## Goal

Establish the final Terraform composition and module contracts before any
Platform V2 AWS resources are implemented.

## Included

- S3 backend declaration
- provider aliases for `us-east-1`, `us-west-2`, and `us-east-2`
- site definitions
- region codes
- common tags
- shared runtime input
- east and west regional module instances
- global edge module instance
- module variables, locals, and outputs
- Terraform tests
- offline validation script

## Excluded

MR-007A creates no AWS resources.

It does not yet include:

- Cognito
- API Gateway
- Lambda
- DynamoDB
- S3
- SQS
- CloudWatch
- CloudFront
- Route 53
- ACM
- frontend deployment
- CI/CD changes

## Safety

Validate this bundle in isolation while Platform V1 remains deployed.

Do not install it over the repository's active `infra/` directory until
Platform V1 has been destroyed using the current configuration.

## Validation

From the extracted bundle:

```bash
./tools/validate_platform_v2_foundation.sh
```

Expected:

```text
Platform V2 foundation validation passed.
```

## Acceptance criteria

- Terraform initializes with the backend disabled.
- Terraform formatting passes.
- Terraform validation passes.
- Terraform tests pass.
- East is `us-east-1` / `use1`.
- West is `us-west-2` / `usw2`.
- Witness is reserved as `us-east-2`.
- East and west have identical active roles.
- East and west receive the same deployment identity.
- No AWS resources are created by the foundation.
