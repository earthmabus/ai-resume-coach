# Repository Structure

This document defines the authoritative top-level organization of the AI Resume Coach repository. Placement is based on responsibility and operator intent rather than implementation chronology.

## Top-level ownership

| Path | Responsibility |
|---|---|
| `src/` | Runtime application code, shared domain behavior, Lambda handlers, and workers. |
| `frontend/` | Static browser assets and client-side application behavior. |
| `infra/` | Terraform composition, reusable infrastructure modules, examples, and Terraform contract tests. |
| `tests/` | Python contract, unit, integration-style, and repository/tooling tests. |
| `tools/` | Supported build, preparation, inspection, validation, and operational entrypoints. |
| `docs/` | Current architecture, engineering, operations, certification, portfolio, history, and archive material. |

Generated artifacts such as deployment ZIPs, Terraform plans, caches, state, and evidence output are not source architecture and must remain ignored or outside the repository.

## Tooling organization

Tooling is grouped by the operator question being answered:

- `tools/build/` — What deployable artifact should be constructed?
- `tools/prepare/` — What prerequisites, credentials, profiles, or plans are needed?
- `tools/inspect/` — What is true about the current environment or evidence?
- `tools/validate/` — Does the repository, infrastructure, or runtime satisfy its contract?
- `tools/operations/` — What explicitly approved mutation or recovery action should occur?
- `tools/lib/` — What shared implementation is sourced by entrypoints?

Each executable category exposes a `run.sh` dispatcher while retaining focused scripts for automation and direct use.

## Test organization

Application behavior tests remain directly under `tests/`. Repository and operator-tooling tests live under `tests/tooling/`. New test groupings should be introduced only when ownership is unambiguous; directory depth should not obscure test discovery.

## Documentation organization

- `docs/architecture/` — current system and repository design
- `docs/engineering/` — delivery practices, implementation slices, and validation contracts
- `docs/operations/` and `docs/runbooks/` — current operator procedures
- `docs/certification/` — formal runtime certification evidence and conclusions
- `docs/history/` — chronological project narrative
- `docs/archive/` — superseded or package-specific material retained for traceability

Archived documents may preserve historical names and paths when necessary, but must clearly identify that they are not current operating instructions.

## Naming rules

Executable names describe capabilities, not milestone identifiers. Milestone identifiers such as `MR-014` belong in engineering and certification documentation. Examples:

- `configuration_profile.py`, not `mr014_tfvars.py`
- `runtime_baseline.sh`, not `mr009d3b_runtime_validation.sh`
- `failover_runtime.sh`, not `mr009d4_runtime_validation.sh`

## Change rules

A structural change is complete only when:

1. supported paths are updated in workflows, tests, and current documentation;
2. old entrypoints are removed rather than retained as duplicate implementations;
3. `pytest -q` and `tools/validate/run.sh terraform` pass;
4. `git diff --check` reports no whitespace errors.
