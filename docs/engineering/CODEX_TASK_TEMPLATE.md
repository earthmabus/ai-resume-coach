# Codex Task Template

Use one bounded slice at a time.

```text
Implement <milestone and slice name>.

Read first:
- AGENTS.md
- docs/engineering/CODEX_WORKING_CONTEXT.md
- docs/engineering/MULTI_SITE_COMPLETION_PLAN.md
- relevant files under docs/architecture/decisions/
- relevant source, tests, Terraform modules, and Terraform tests

Before editing:
1. Inspect the repository.
2. Summarize existing behavior and abstractions.
3. Identify exact files likely to change.
4. Call out conflicts or ambiguity.
5. Propose a narrow plan.
6. Do not edit until the plan is accepted.

Architectural constraints:
- Keep the current single-table DynamoDB design.
- Keep processing_queue and processing_dlq generic.
- Preserve public API and SQS compatibility unless explicitly authorized.
- Runtime identity is diagnostic only.
- Reuse centralized configuration and existing context abstractions.
- Do not add a logging framework without evidence it is necessary.
- Do not add paid AWS services.
- Do not deploy, apply Terraform, or commit.

Implementation:
- Make the smallest coherent change.
- Update focused tests.
- Update durable documentation only where the decision or behavior changed.
- Do not perform unrelated cleanup.

Validation:
- Run focused tests first.
- Run the commands in docs/engineering/VALIDATION_CONTRACT.md.
- Report exact outputs and pass/fail counts.

Completion report:
1. Repository assessment
2. Design implemented
3. Files changed
4. Contract impact
5. Tests added or changed
6. Exact validation results
7. Risks, ambiguities, and follow-up items
```
