# MS-004: Runtime Identity Is Diagnostic Metadata

## Status

Accepted direction; implementation pending

## Decision

Provide consistent runtime identity for API and worker executions using centralized configuration and existing runtime abstractions.

Candidate fields:

- AWS region
- logical site
- environment
- deployment ID
- application version
- Lambda function name, when available

## Rationale

Operators must be able to determine which regional site and deployment handled a request or unit of work. This supports failover validation, incident diagnosis, log correlation, and rollback verification.

## Constraints

Runtime identity:

- is diagnostic metadata
- must be deterministic in tests
- should use safe fallbacks for local execution
- should avoid scattered direct environment reads
- may be included in safe health responses and structured logs

Runtime identity must not:

- authorize requests
- select tenants
- make routing decisions
- become authoritative business data
- expose secrets, account IDs, ARNs, table names, bucket names, queue URLs, tokens, or credentials

## Implementation Guidance

Inspect before choosing an abstraction:

- `src/core/config.py`
- `src/core/request_context.py`
- real API handler implementation
- real worker handler implementation
- health route implementation
- existing logging statements
- regional Lambda environment configuration
- related Python and Terraform tests

Do not introduce a logging or telemetry framework unless the current implementation demonstrates a concrete need.
