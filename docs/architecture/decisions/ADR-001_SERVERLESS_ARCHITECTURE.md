# ADR-001: Adopt Serverless Architecture

## Status

Accepted

## Date

2026-06-14

## Context

The project requires:

* Low operational overhead
* Minimal infrastructure management
* Low monthly operating costs
* Rapid iteration
* Demonstration of modern AWS architecture patterns

## Decision

Use a serverless architecture based on:

* AWS Lambda
* Amazon API Gateway
* Amazon DynamoDB
* Amazon S3
* Amazon CloudFront

Infrastructure will be managed using Terraform.

Deployment will be performed through GitHub Actions using OIDC federation.

## Consequences

### Positive

* Near-zero idle infrastructure cost
* No server management
* Automatic scaling
* Simplified operations
* Faster development cycles

### Negative

* Cold start considerations
* Vendor-specific implementation
* API Gateway limits
* Lambda execution limits

## Alternatives Considered

### Amazon ECS Fargate

Rejected due to additional operational complexity and cost.

### Amazon EKS

Rejected due to operational overhead inappropriate for portfolio-scale workloads.

### EC2

Rejected due to infrastructure management burden.

## Outcome

The serverless architecture best aligns with project goals of simplicity, security, scalability, and cost control.

