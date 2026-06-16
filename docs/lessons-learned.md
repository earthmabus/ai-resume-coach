# Lessons Learned

## Infrastructure as Code Matters

Terraform made it possible to repeatedly deploy environments and recover from configuration mistakes.

## OIDC is Worth the Setup Effort

GitHub Actions OIDC eliminated long-lived AWS credentials and significantly improved security.

## Async Processing Was Necessary

AI requests frequently exceeded API Gateway limits.

Moving AI workloads to SQS and a Worker Lambda solved:

* Timeouts
* Poor user experience
* Reliability concerns

## PDF Processing is More Complex Than Expected

PDFs require:

* Storage
* Parsing
* Error handling
* Validation

Converting PDFs into the same internal representation as text resumes simplified downstream processing.

## Provider Abstraction Paid Off

Separating AI provider logic from business logic reduced complexity and improved maintainability.

## Frontend UX Matters

The project evolved significantly after initial functionality was completed.

Major improvements included:

* Multi-page navigation
* Search
* Sorting
* Resume previews
* Job previews
* Download functionality
* Responsive layouts

## Cloud Cost Awareness

The architecture was intentionally designed around:

* Lambda
* S3
* DynamoDB
* SQS

to minimize operational costs while supporting portfolio-quality functionality.

## AI Product Design Is Different

AI features require:

* Async workflows
* Status tracking
* Retry strategies
* Fallback providers
* User feedback during processing

Traditional synchronous request-response patterns are often insufficient.

