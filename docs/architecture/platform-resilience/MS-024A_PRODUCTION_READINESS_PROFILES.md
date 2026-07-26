# MS-024A — Production Readiness Profiles

## Purpose

MS-024A makes the readiness certification reusable across development, integration, pre-production, and production environments. It preserves one validation engine while changing only the policy applied to environment-specific controls.

## Profiles

| Profile | Intended use | Cognito WAF | Alarm notifications | Terraform production enforcement |
|---|---|---|---|---|
| `development` | Developer-owned or temporary cloud environment | Optional | Optional | Optional |
| `integration` | Shared integration and system testing | Recommended | Recommended | Recommended |
| `pre-production` | Staging/UAT with production-equivalent resilience | Recommended | Recommended | Recommended |
| `production` | Internet-facing production deployment | Required | Required | Required |

Architecture, multi-region reliability, health, observability inventory, structured logging, encryption, PITR, and the durable MR-014 resilience certification remain required in every profile.

## Decision model

- `<PROFILE>_CERTIFIED`: every control required by the selected profile passes.
- `PRODUCTION_CERTIFIED_WITH_EXCEPTIONS`: production-required controls pass, with other documented warnings.
- `NOT_CERTIFIED`: one or more controls required by the selected profile fail.

Warnings remain visible in evidence but do not block development, integration, or pre-production certification when the profile explicitly treats that control as recommended rather than required.

`productionReady` is true only for a passing `production` profile. A passing pre-production assessment reports `profileReady: true` and `productionReady: false`.

## Commands

Assess the default pre-production profile:

```bash
./tools/resilience/activate_production_readiness_certification.sh assess
```

Assess a specific profile:

```bash
./tools/resilience/activate_production_readiness_certification.sh assess --profile development
./tools/resilience/activate_production_readiness_certification.sh assess --profile integration
./tools/resilience/activate_production_readiness_certification.sh assess --profile pre-production
./tools/resilience/activate_production_readiness_certification.sh assess --profile production
```

Publish a durable profile-specific record only after that profile passes:

```bash
./tools/resilience/activate_production_readiness_certification.sh certify --profile pre-production
```

The record is written beneath `docs/certification/` with the profile in its filename. No AWS mutations are performed.

## Current expected result

The current deployment is expected to achieve `PRE_PRODUCTION_CERTIFIED` with accepted warnings for:

- Cognito WAF not enabled.
- Alarm notification actions not configured.
- Terraform production-readiness enforcement disabled.
- Terraform still reporting the production-only `cognito_waf` control as missing.

The same deployment must remain `NOT_CERTIFIED` under the `production` profile until those controls are enabled and validated.
