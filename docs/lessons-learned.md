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


## Multi-Site Completion Requires Evidence, Not Just Symmetry

Deploying equivalent resources in two regions was only the starting point. A defensible active-active claim required proving routing isolation, deterministic ownership, replicated reads, durable backlog, idempotency, worker restoration, queue drain, and final reconciliation.

The most useful closeout artifact was a bounded certification contract that stated both what was proven and what remained outside scope.

## Intermediate Validation Reports Must Be Clearly Superseded

MR-009D3B exposed genuine prerequisites, but its historical reports continued to contain open-status language after later slices and MR-014 had superseded them. Closeout documentation should preserve the chronology while adding an unmistakable current-status banner and links to authoritative acceptance records.

## Build Tooling Must Derive the Repository Root Consistently

Moving scripts into a deeper `tools/` taxonomy exposed copied assumptions about directory depth. Build, validation, and operational scripts must derive the repository root from their actual file location and have regression coverage that runs from non-root working directories.

A related test-harness issue occurred when running `python -c` from inside `tools/`: the local `tools/inspect` package shadowed Python's standard-library `inspect` module. Isolated-mode subprocesses (`python -I`) prevented the test environment from changing import resolution.

## CI Is Part of the Architecture Evidence

The final successful workflow did more than confirm syntax. It proved that a clean checkout could compile the code, execute the full test suite, construct architecture-specific Lambda artifacts, initialize and validate Terraform, produce a plan against the deployed multi-region state, and apply the resulting changes.
