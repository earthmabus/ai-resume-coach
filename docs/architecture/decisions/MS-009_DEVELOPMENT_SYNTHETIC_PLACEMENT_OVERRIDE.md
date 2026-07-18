# MS-009 Development Synthetic Placement Override

## Status

Accepted for development runtime validation.

## Context

MR-009D must prove both local and cross-region asynchronous processing in the
deployed active-active development runtime. The accepted ownership model
separates runtime region from owner region, and the outbox transport already
uses persisted `ownerRegion` to choose the processing queue.

Normal business API creation currently defaults new asynchronous resume
analysis work to the receiving active region. That behavior is correct for
current product use, but it cannot produce an east-initiated west-owned item
or a west-initiated east-owned item through supported APIs.

Direct DynamoDB writes, manual ownership mutation, manual outbox creation, and
manual SQS sends are not valid runtime evidence.

## Decision

Add a narrowly controlled development-only validation mechanism for initial
uploaded-resume analysis creation:

- request header: `X-Validation-Owner-Region`;
- enabled only when `ENVIRONMENT=dev`;
- disabled by default through `ENABLE_SYNTHETIC_PLACEMENT_OVERRIDE=false`;
- explicitly enabled by deployment variable
  `enable_synthetic_placement_override=true`;
- requires Cognito JWT authentication;
- requires membership in the configured Cognito group
  `synthetic-runtime-validation`;
- accepts only configured active regions;
- rejects the MRSC witness region;
- applies only during initial asynchronous work creation;
- records `ownerRegion` and `syntheticPlacementOverrideUsed`;
- includes owner region and override use in the idempotency fingerprint;
- does not alter existing ownership;
- does not use health state as routing or placement authority.

## Consequences

MR-009D3B can create remote-owned synthetic development work through the same
durable work, idempotency, outbox, queue, worker, and persistence path used by
normal uploaded-resume analysis.

Normal callers cannot use the mechanism without both the explicit development
deployment setting and the dedicated validation group claim. Production and
stage deployments reject the override by Terraform validation and application
runtime checks.

The mechanism is validation infrastructure, not a public business-domain
ownership feature. It may be removed after active-active runtime validation is
complete unless later decision work explicitly promotes deterministic
production placement.
