# PDF Lambda Layer Repository-Root Fix

## Problem

The CLI default in `tools/build/pdf_dependency_layer.py` resolved to the `tools/`
directory (`Path(__file__).resolve().parents[1]`). As a result, CI looked for:

`tools/lambda_layer/requirements.txt`

The actual requirements file is:

`lambda_layer/requirements.txt`

## Changes

- Correct the CLI repository root default to `Path(__file__).resolve().parents[2]`.
- Add a regression test confirming the default resolves to the repository root and
  locates the committed Lambda-layer requirements file.

## Validation

Run from the repository root:

```bash
python -m compileall src tools tests
python -m pytest -q
python tools/build/pdf_dependency_layer.py
```
