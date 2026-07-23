# Repository Root Audit Fix

## Scope

Audited repository tooling for file-relative repository-root calculations after CI exposed two off-by-one defaults under `tools/`.

## Corrected files

- `tools/build/lambda_packages.py`
  - Changes the default repository root from `parents[1]` (`tools/`) to `parents[2]` (repository root).
- `tools/validate/lambda_artifacts.py`
  - Applies the same correction so artifact validation resolves `build/` from the repository root.
- `tools/operations/replay_outbox.py`
  - Applies the same correction so its bootstrap adds `<repository>/src`, not `<repository>/tools/src`, to `sys.path`.
- `tests/tooling/test_repository_root_defaults.py`
  - Adds regression coverage for all three file-relative defaults, including execution from a non-root working directory.

## Audit result

The remaining Python `Path(__file__).resolve().parents[...]` usages were reviewed. Their depths are appropriate for their locations:

- files directly under `tests/` use `parents[1]`
- files under `tests/tooling/` use `parents[2]`
- files under `tools/<category>/` that need repository root use `parents[2]`

Shell tooling consistently resolves the repository root with `../..` from `tools/<category>/` and did not require changes.

## Validation performed

- `python -m compileall src tools tests`
- full test suite: `576 passed, 1 skipped`
- focused root/default and package-builder tests: `10 passed, 1 skipped`
- `python tools/build/lambda_packages.py` completed successfully and produced all four package directories

`tools/validate/lambda_artifacts.py` was not fully executable in the extracted context because the generated PDF dependency layer was not present there; its corrected default is directly covered by the regression test.
