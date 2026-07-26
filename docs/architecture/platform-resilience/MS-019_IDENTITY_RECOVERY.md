# MS-019 — Cognito Identity Recovery Foundation

## Decision

Amazon Cognito user pools do not provide native cross-Region user-pool
replication. Password verifiers, refresh tokens, hosted domains, pool IDs, and
JWT issuers cannot be copied into a second Region as a seamless active-active
identity plane.

MS-019 therefore establishes an honest **warm-standby recovery foundation** in
`us-west-2`; it does not label that foundation as multi-Region identity.

## Scope

This slice provisions a standby user pool, web client, and hosted domain in
`us-west-2` with the same user-facing password and attribute contract as the
primary pool.

The standby pool is intentionally not connected to the application during
normal operation. During a complete `us-east-1` identity outage, recovery still
requires an operator-controlled migration of available user attributes and a
password-reset flow for restored users.

## Commands

```bash
./tools/resilience/activate_identity_recovery.sh plan

# Review the saved plan and changes.tsv, then:
CONFIRM_MUTATION=YES ./tools/resilience/activate_identity_recovery.sh apply

./tools/resilience/activate_identity_recovery.sh validate
```

The plan consumes the generated MS-018 routing tfvars so identity activation
cannot accidentally disable the already-deployed global API edge.

## Explicit limitations

- Passwords are not replicated.
- Existing refresh tokens and sessions are not replicated.
- The standby pool has a different issuer and client ID.
- API authorizers and frontend configuration do not fail over automatically.
- Users restored into the standby pool must reset their passwords.

For those reasons the MS-017 readiness score remains **80/100** after this
slice. The platform must not be described as surviving loss of `us-east-1`
identity without user disruption.

## Completion criteria

- A standby Cognito pool exists in `us-west-2`.
- Its client supports the same explicit authentication flows as the primary.
- Terraform exposes the `cognito_recovery` contract.
- Validation confirms the recovery mode and its limitations.
- No production authorizer or frontend authentication configuration changes.
