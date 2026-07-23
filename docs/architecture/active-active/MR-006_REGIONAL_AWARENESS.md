# MR-006A — Internal Regional Provenance

## Purpose

Prepare the persistence and processing layers for active-active operation
without changing public API or frontend contracts.

## Included

- Runtime identity helper
- Request context region, deployment, and environment
- DynamoDB creation and update provenance
- Worker processing provenance
- Outbox-record deployment provenance
- Replay provenance
- Structured Lambda logs

## Persistent metadata

New or updated records use:

- `createdRegion`
- `createdByDeploymentId`
- `lastUpdatedRegion`
- `lastUpdatedByDeploymentId`

Worker-completed records additionally use:

- `processedRegion`
- `processedByDeploymentId`
- `processedAt`

## Outbox compatibility

The outbox record stores deployment provenance, but the existing worker
payload remains unchanged. The deterministic event ID and SQS message
contract therefore remain backward compatible.

## Explicitly deferred to MR-006B

- Runtime metadata on all API response bodies
- New runtime HTTP headers
- Frontend region/deployment badges
- Any new public runtime endpoint

The existing health and version endpoints continue to provide runtime
identity where already supported.

## Validation

```bash
python tools/build/lambda_packages.py
python -m compileall src tests tools

pytest -q tests/test_runtime_identity.py
pytest -q tests/test_request_context.py
pytest -q tests/test_outbox.py
pytest -q tests
```
