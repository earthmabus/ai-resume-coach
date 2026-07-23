# CI Import Resolution Fix

This overlay addresses the GitHub Actions collection failure:

```text
ModuleNotFoundError: No module named 'tools.build'
```

## Changes

- Makes repository import-path precedence deterministic in `tests/conftest.py`, preventing unrelated site-packages named `tools` from shadowing the repository's `tools` package.
- Runs tests through `python -m pytest -q` in CI.
- Compiles `src`, `tools`, and `tests` in CI.
- Adds `tools/**` to the Terraform workflow path trigger.
- Adds an import-resolution regression test.
- Removes the Pytest 10 iterator deprecation warning from the workflow-state matrix test.

## Validation performed

```text
python -m compileall -q src tools tests
python -m pytest -q
572 passed, 1 skipped
```
