# MR-010A Known Status Import Fix

This overlay contains a full replacement for:

    src/lambdas/worker/handler.py

It preserves the temporary CLAIM DEBUG diagnostics and adds the missing
`known_status` import from `core.workflow_state`.

## Apply from the repository root

    unzip -o ~/Downloads/MR010A_known_status_full_replacement_overlay.zip -d .

## Validate

    python -m compileall src tests
    python -m pytest -q

After the tests pass, commit/push normally so GitHub Actions can deploy it.

Then submit a NEW PDF analysis and inspect the worker logs for a line beginning:

    CLAIM DEBUG:

Capture these fields:

- status
- type
- allowed
- known
- can_transition
