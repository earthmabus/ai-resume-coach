# CI Import Resolution Fix — Root Cause Correction

This overlay corrects the GitHub Actions failure:

```text
ModuleNotFoundError: No module named 'tools.build'
```

## Root cause

The repository's generic `build/` ignore rule also matched `tools/build/`.
The files existed locally, so local tests passed, but Git did not include that
package in the commit. GitHub Actions therefore checked out `tools/` without
`tools/build/`.

The workflow diagnostics confirmed this distinction:

- the job ran Python tests from the repository root;
- the checked-out `tools` package existed;
- `tools/build` was absent from the runner checkout.

## Changes

- `.gitignore`
  - explicitly unignores `tools/build/` and everything beneath it;
- `.github/workflows/terraform.yml`
  - removes the temporary repository-layout diagnostic step;
  - retains repository-root working directories for Python tests and package builds;
- `tools/build/**`
  - includes the complete build-tooling package so Git can add it after the
    ignore correction.

## Apply and verify

After extracting this overlay at the repository root, run:

```bash
git status --short
git check-ignore -v tools/build/pdf_dependency_layer.py || true
python -m compileall src tools tests
python -m pytest -q
```

`git status --short` should show the `tools/build` files as newly trackable
unless they were already force-added. `git check-ignore` should produce no
matching ignore rule for the file.
