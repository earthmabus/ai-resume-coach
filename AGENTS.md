# AI Resume Coach Repository Guidance

## Mission

Build and operate a secure, observable, cloud-native AI Resume Coach while preserving a clear separation between product domains and reusable platform capabilities.

## Sources of Truth

Before editing, inspect the repository rather than relying on assumptions.

- Product and architecture documentation: `docs/`
- Durable multi-site decisions: `docs/architecture/decisions/`
- Current multi-site working context: `docs/engineering/CODEX_WORKING_CONTEXT.md`
- Remaining multi-site roadmap: `docs/engineering/MULTI_SITE_COMPLETION_PLAN.md`
- Terraform architecture contracts: `infra/tests/`
- Platform validation: `tools/validate/platform_v2_foundation.sh`
- Application behavior: `src/` and `tests/`
- Lambda package construction: `tools/build/lambda_packages.py`

When documentation and executable tests conflict, stop and report the conflict. Do not silently choose one.

## Current Architecture

- Active application sites: `us-east-1` and `us-west-2`
- DynamoDB MRSC witness region: `us-east-2`
- Current DynamoDB design: one table
- Shared asynchronous capability:
  - `processing_queue`
  - `processing_dlq`
- API and worker Lambdas are regional peers.
- Runtime configuration is centralized in `src/core/config.py`.
- Per-request API context is represented in `src/core/request_context.py`.
- Root `handler.py` and `worker.py` files are compatibility entrypoints and should remain thin.
- Public health and liveness behavior must remain backward compatible unless a task explicitly changes it.

## Ubiquitous Language

Use domain-specific names for authoritative Resume Analysis data:

- `resume_analysis`
- `resume_analysis_table`
- `RESUME_ANALYSIS_TABLE`
- `resume_analysis_data`
- `resume_analysis_contract`

Use capability-oriented names for shared asynchronous infrastructure:

- `processing_queue`
- `processing_dlq`

A consuming feature may use a domain-facing environment variable when that variable describes how the feature reaches the shared capability. Do not rename shared Terraform resources merely to match a consuming feature.

## Non-Negotiable Decisions

- Retain the current single-table DynamoDB design unless a task explicitly reopens that decision.
- Retain the shared processing queue and DLQ.
- Do not split queues merely because messages represent different work types.
- Queue separation requires a material difference in scaling, latency, retry policy, security, failure isolation, or operational ownership.
- Keep outbox and idempotency behavior compatible.
- Do not change SQS message contracts incidentally.
- Runtime identity is diagnostic metadata, not an authorization, tenancy, or routing mechanism.
- Do not expose secrets, account IDs, ARNs, table names, bucket names, or queue URLs in public health responses.
- Do not add paid AWS services without explicit approval.
- Do not deploy, run `terraform apply`, or commit unless explicitly requested.

## Working Method

1. Inspect relevant code, tests, Terraform, and documentation.
2. Summarize the current behavior and identify ambiguities.
3. Propose a narrow implementation plan with exact files.
4. Prefer existing abstractions over parallel frameworks.
5. Preserve compatibility unless the task explicitly authorizes a contract change.
6. Add or update focused tests with implementation changes.
7. Run the required validation.
8. Report exact results, remaining risks, and any documentation/code disagreement.

For ambiguous architecture decisions, stop after planning and ask for direction.

## Change Discipline

- Prefer small, reviewable slices.
- Avoid opportunistic refactoring.
- Avoid new frameworks when a small module or existing abstraction suffices.
- Do not scatter direct environment-variable reads across handlers; use centralized configuration.
- Keep immutable configuration and request-context objects where existing patterns support them.
- Do not turn diagnostic context into business state.
- Preserve generic shared infrastructure naming.

## Validation

Follow `docs/engineering/VALIDATION_CONTRACT.md`.

At minimum, relevant changes should run:

```bash
python -m compileall src tests
pytest -q tests
cd infra
terraform fmt -recursive -check
terraform validate
cd ..
./tools/validate/platform_v2_foundation.sh
```

Use focused tests first, then the full suite. Report exact pass/fail counts.
