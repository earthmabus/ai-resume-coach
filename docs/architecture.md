# AI Resume Coach - Architecture Overview

## Purpose

AI Resume Coach is a cloud-native application that analyzes resumes and provides actionable recommendations to improve candidate positioning, clarity, and effectiveness.

The initial implementation focuses on establishing a secure, automated deployment pipeline and serverless application architecture.

## Goals

* Demonstrate modern cloud-native architecture patterns
* Demonstrate Infrastructure as Code (IaC) using Terraform
* Demonstrate secure CI/CD using GitHub Actions and AWS OIDC federation
* Provide a foundation for future AI-powered resume analysis capabilities

## Architecture

### Current Architecture

Client

↓

S3 Static Website

↓

Amazon API Gateway

↓

AWS Lambda

↓

Amazon CloudWatch Logs

### Planned Architecture

Client

↓

CloudFront

↓

Static Frontend (S3)

↓

API Gateway

↓

Lambda

↓

Resume Analysis Service

↓

Amazon Bedrock / LLM Provider

↓

DynamoDB

## Infrastructure Management

All infrastructure is managed through Terraform.

No manual infrastructure changes are intended after initial bootstrap.

## Security

### Authentication

GitHub Actions uses OpenID Connect (OIDC) federation to assume AWS IAM roles.

No long-lived AWS access keys are stored in GitHub.

### IAM

Least privilege principles will be applied to deployment roles and application execution roles.

Current Roles
* GitHubActionsDeployRole - Used for deployment validation and AWS access verification.
* GitHubActionsTerraformRole-ai-resume-coach - Used for Terraform infrastructure deployment.
* Lambda Execution Role - Used by the application runtime.

### Encryption

AWS-managed encryption is enabled where supported.

## Cost Management

The project is deployed into a dedicated AWS portfolio account.

Controls include:

* AWS Budgets
* AWS Cost Anomaly Detection
* Separate AWS account isolation
* Serverless-first architecture

## Deployment

Deployment is fully automated through GitHub Actions.

Workflow:

GitHub Push

↓

GitHub Actions

↓

OIDC Federation

↓

Terraform Apply

↓

AWS Infrastructure Update

## Current Endpoints

GET /health

Returns application health status.

GET /version

Returns application version information.

POST /analyze-resume

Returns resume analysis results.

(Current implementation uses placeholder analysis responses.)

## Future Enhancements

* AI-powered resume analysis
* Interview preparation recommendations
* Resume scoring engine
* Historical analysis storage
* User authentication
* Multi-model AI support

