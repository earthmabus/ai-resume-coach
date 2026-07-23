# MR-009D3C — Global API Edge

## Objective

Deploy one shared API hostname across the active `us-east-1` and `us-west-2` Regional HTTP APIs so runtime isolation and recovery can be validated in MR-009D4.

## Certificate ownership decision

ACM certificate lifecycle is intentionally external to Terraform.

The deployment consumes:

- one issued ACM certificate in `us-east-1`;
- one issued ACM certificate in `us-west-2`;
- both certificates covering the shared API hostname.

This keeps the global-edge plan deterministic and avoids apply-time ACM DNS validation values being used as Terraform resource keys.

## Resulting topology

```text
api.resume.michaelpopovich.com
          |
          +-- Route 53 latency alias -- us-east-1 Regional API custom domain
          |
          +-- Route 53 latency alias -- us-west-2 Regional API custom domain
```

Each custom domain maps its `$default` base path to the existing Regional HTTP API.

## Prepare certificates

From the repository root:

```bash
export AWS_PROFILE=<profile>

tools/prepare/external_acm_certificates.sh
```

The helper:

1. reuses an existing issued or pending certificate when available;
2. otherwise requests the certificate in each API Region;
3. publishes the ACM DNS validation CNAME in the configured hosted zone;
4. waits for both certificates to become issued;
5. writes `infra/global-api-routing.generated.tfvars`.

The helper does not run Terraform.

Optional overrides:

```bash
export DOMAIN_NAME=api.resume.michaelpopovich.com
export HOSTED_ZONE_ID=Z074065915GNYUCPJUVGS
export OUTPUT_TFVARS="$PWD/infra/global-api-routing.generated.tfvars"
```

## Deploy

```bash
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate
terraform -chdir=infra test

terraform -chdir=infra plan \
  -input=false \
  -var-file=global-api-routing.generated.tfvars \
  -out=global-api-routing.tfplan

terraform -chdir=infra show global-api-routing.tfplan
terraform -chdir=infra apply global-api-routing.tfplan
```

Expected additions:

- two Regional API Gateway custom domains;
- two `$default` API mappings;
- two Route 53 latency alias records.

The plan should not replace the active Regional APIs, shared identity, DynamoDB, SQS, Lambda functions, or S3 resources.

## Validate

```bash
TFVARS_FILE="$PWD/infra/global-api-routing.generated.tfvars" \
  tools/validate/global_api_edge.sh
```

Then rerun the MR-009D4 read-only preflight:

```bash
tools/validate/failover_runtime.sh
```

## Rollback

Disable the global edge while retaining the Regional APIs:

```bash
terraform -chdir=infra plan \
  -input=false \
  -var-file=global-api-routing.generated.tfvars \
  -var='enable_global_api_routing=false' \
  -out=disable-global-api-routing.tfplan

terraform -chdir=infra show disable-global-api-routing.tfplan
terraform -chdir=infra apply disable-global-api-routing.tfplan
```

The external ACM certificates and their DNS validation record remain outside Terraform and are not deleted by rollback.
