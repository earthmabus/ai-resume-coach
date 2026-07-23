# Repository Root Test Isolation Fix

## Problem

The repository-root regression test executed `python -c` with `cwd=tools`.
That made the repository's `tools/inspect` package shadow Python's standard-library
`inspect` module during transitive imports, causing an unrelated failure before the
bootstrap assertions could run.

## Resolution

Run the subprocess with Python isolated mode (`-I`). This preserves the deliberate
non-root working directory while preventing the current working directory from being
added to `sys.path`.

## Files

- `tests/tooling/test_repository_root_defaults.py`

## Validation

- `python -m pytest -q tests/tooling/test_repository_root_defaults.py`
- Result: `3 passed`
