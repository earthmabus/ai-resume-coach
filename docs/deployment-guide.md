# Deployment Guide

## Prerequisites

Required:

* AWS Account
* Terraform
* AWS CLI
* GitHub Repository
* OpenAI API Key

## Configure GitHub Secrets

Repository Settings → Secrets and Variables → Actions

Required:

OPENAI_API_KEY

## Deploy Infrastructure

```bash
cd infra

terraform init

terraform plan

terraform apply
```

## Deploy Application

Push to GitHub:

```bash
git add .
git commit -m "Deploy changes"
git push
```

GitHub Actions automatically:

* Validates Terraform
* Builds Lambda packages
* Deploys infrastructure
* Deploys frontend assets

## Verify Deployment

Health endpoint:

```bash
curl https://<api-id>.execute-api.us-east-1.amazonaws.com/health
```

Version endpoint:

```bash
curl https://<api-id>.execute-api.us-east-1.amazonaws.com/version
```

Resume analysis:

```bash
curl -X POST https://<api-id>.execute-api.us-east-1.amazonaws.com/analyze-resume \
  -H "Content-Type: application/json" \
  -d '{"resumeText":"Sample resume"}'
```

## Monitoring

View Lambda logs:

```bash
aws logs tail /aws/lambda/ai-resume-coach-dev-api \
  --region us-east-1
```

Worker logs:

```bash
aws logs tail /aws/lambda/ai-resume-coach-dev-worker \
  --region us-east-1
```

## Common Issues

### CORS Errors

Verify API Gateway CORS configuration.

### Missing OpenAI Key

Verify GitHub Actions secret:

OPENAI_API_KEY

### SQS Jobs Not Processing

Verify:

* Worker Lambda deployment
* Event source mapping
* SQS permissions

### PDF Upload Failures

Verify:

* S3 upload bucket
* PDF layer build with `python tools/build_pdf_dependency_layer.py`
* Lambda package build with `python tools/build_lambda_packages.py`
* Deployment artifact validation with `python tools/validate_lambda_artifacts.py`
* PDF layer attachment on the regional API Lambdas
* Lambda memory settings
