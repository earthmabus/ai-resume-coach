# MS-018 — Global API Routing

## Goal

Activate the existing Route 53 latency-routing design across the `us-east-1`
and `us-west-2` regional APIs, with health checks against `/health/ready`.

## Scope

This slice does not change Cognito, S3 document continuity, DynamoDB, queues, or
worker ownership. It activates only the already-implemented global API edge.

## Commands

```bash
./tools/resilience/activate_global_api_routing.sh prepare
./tools/resilience/activate_global_api_routing.sh plan

# Review the plan and changes.tsv in the reported evidence directory, then:
CONFIRM_MUTATION=YES ./tools/resilience/activate_global_api_routing.sh apply

./tools/resilience/activate_global_api_routing.sh validate
```

The prepare step requests or reuses Regional ACM certificates in both active
Regions and writes the ignored local file
`infra/global-api-routing.generated.tfvars`. The generated profile enables both
latency records and both Route 53 endpoint health checks.

The plan step no longer composes the retired `runtime-validation.tfvars`
profile. It uses normal Terraform inputs, overlays the generated routing
variables, reads the deployed Lambda runtime identity, and explicitly aligns the
plan to the deployed `deployment_id` and `analysis_provider`. The reviewed plan
is saved under `infra/.terraform-build/` and is the exact plan consumed by the
apply step.

## Completion criteria

- Both direct regional `/health/ready` endpoints pass.
- `api.resume.michaelpopovich.com` resolves and its readiness endpoint passes.
- Terraform output reports latency routing enabled.
- Terraform output reports Route 53 health checks enabled.
- The readiness score increases from 45 to 80.

The platform is still not declared outage-ready because identity and document
storage remain single-Region dependencies.
