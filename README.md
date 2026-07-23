# MR-010A Resume Analysis Worker Claim Fix

This overlay contains full replacement files.

## Root cause addressed

The deployed worker rejected resume-analysis records whose persisted status was `QUEUED`, causing repeated SQS retries and eventual DLQ placement.

The fix makes the authoritative workflow transition matrix the source of truth for claimability, while retaining job-specific restrictions. It also expands the runtime error message to include the job type and authorized claimable statuses.

## Files

- `src/lambdas/worker/handler.py`
- `tests/test_worker_claim_states.py`

## Apply

From the repository root:

```bash
unzip -o MR010A_resume_analysis_worker_claim_fix_overlay.zip -d .
python -m compileall src tests
pytest -q
python tools/build/lambda_packages.py
terraform -chdir=infra plan -input=false -out=tfplan
terraform -chdir=infra apply -input=false tfplan
```

## Validation performed

```text
578 passed, 1 skipped
```

After deployment, submit a fresh PDF analysis. Do not redrive old DLQ messages until the new worker deployment is confirmed healthy.
