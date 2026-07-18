# AI-Assisted Development

This directory documents the lightweight engineering lifecycle used for
AI-assisted work in this repository.

Use it when a change needs more than a small task description: architecture
intent, bounded implementation, readiness review, operational review, durable
decisions, or merge-readiness evidence. Low-risk maintenance can still use the
existing [Codex task template](../CODEX_TASK_TEMPLATE.md) and
[validation contract](../VALIDATION_CONTRACT.md).

## Documents

- [AI Engineering Playbook](AI_ENGINEERING_PLAYBOOK.md): end-to-end lifecycle,
  roles, authority, scope, validation, and merge discipline.
- [EDS Template](EDS_TEMPLATE.md): Engineering Design Specification for a
  bounded implementation slice.
- [ARR Template](ARR_TEMPLATE.md): Architectural Readiness Review template.
- [ORR Template](ORR_TEMPLATE.md): Operational Readiness Review template.
- [Review Decision Record Template](REVIEW_DECISION_RECORD_TEMPLATE.md):
  lightweight record for accepted review decisions that should remain durable.

## Normal Workflow

```text
Architecture intent
  -> Engineering Design Specification
  -> AI implementation
  -> Architectural Readiness Review
  -> Operational Readiness Review, when operational boundaries change
  -> human engineering decision
  -> validation
  -> repository documentation and decisions
  -> merge
```

The repository remains the source of truth. AI output is evidence and
recommendation, not final authority.
