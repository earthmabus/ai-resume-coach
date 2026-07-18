# Platform Architecture Book

This package bootstraps the Platform V2 Architecture Book.

## Reading Order
01. Executive Overview
02. Business Goals
03. Architecture Overview
04. System Context
05. Active-Active Architecture
06. Request Lifecycle
07. Data Architecture
08. Processing Architecture
09. Security Architecture
10. Observability
11. Disaster Recovery
12. Deployment Architecture
13. Operational Runbook
14. Architectural Decisions
15. Future Evolution

# Codex Context Package

This package contains repository guidance and durable architectural context for continuing the AI Resume Coach multi-site program with Codex.

## Merge

From the repository root:

```bash
unzip /path/to/ai-resume-coach-codex-context.zip -d /tmp/ai-resume-coach-codex-context
cp -R /tmp/ai-resume-coach-codex-context/ai-resume-coach-codex-context/. .
git diff -- AGENTS.md docs/engineering docs/architecture/decisions
```

Review the files before committing. The package intentionally contains documentation and agent guidance only; it does not modify application or Terraform code.

## Contents

- `AGENTS.md`: concise repository instructions for coding agents
- `docs/engineering/CODEX_WORKING_CONTEXT.md`: current platform state and vocabulary
- `docs/engineering/MULTI_SITE_COMPLETION_PLAN.md`: remaining multi-site work
- `docs/engineering/CODEX_TASK_TEMPLATE.md`: bounded-task prompt template
- `docs/engineering/VALIDATION_CONTRACT.md`: required validation commands
- `docs/architecture/decisions/MS-001_MULTI_SITE_TOPOLOGY.md`
- `docs/architecture/decisions/MS-002_SINGLE_TABLE_FOR_NOW.md`
- `docs/architecture/decisions/MS-003_SHARED_PROCESSING_CAPABILITY.md`
- `docs/architecture/decisions/MS-004_RUNTIME_IDENTITY.md`
