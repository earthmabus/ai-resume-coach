# Platform V2 Teardown and Rebuild Runbook

## Completed prerequisites

- DynamoDB backup created;
- documents synchronized locally;
- Terraform state exported;
- Git working tree clean;
- obsolete additive MR-007 changes reverted.

## Safety checks

Using the current Platform V1 configuration:

```bash
cd ~/Projects/ai-resume-coach/infra
terraform validate
terraform plan -destroy -out=tfplan-platform-v1-destroy
terraform show -no-color tfplan-platform-v1-destroy
```

Confirm the Route 53 hosted zone is a data source and is not destroyed.

## Destroy Platform V1

```bash
terraform apply tfplan-platform-v1-destroy
```

Do not replace Terraform source files before this destroy completes.

## Confirm deletion

```bash
terraform state list
```

Investigate retained buckets, CloudFront delays, IAM propagation, or remaining subscriptions.

## Install Platform V2

Replace old Terraform files, explicitly delete obsolete files, then run:

```bash
terraform init -reconfigure
terraform fmt -recursive
terraform validate
terraform test
terraform plan -input=false -out=tfplan-platform-v2
terraform apply tfplan-platform-v2
```

## Validate

Confirm shared edge/identity, re-register the test user, verify east and west
health/version endpoints, enable explicitly authorized outbox publisher
schedules only when required for the deployment stage, verify scheduled
publisher invocation without manual Lambda invocation, test PDF upload and
processing in each Region, and finish with a no-change Terraform plan.

Forward correction is preferred after destructive rebuild begins. Restore Platform V1 only if Platform V2 cannot be completed within the accepted development window.
