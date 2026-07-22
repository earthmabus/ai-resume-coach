# AI Resume Coach

AI Resume Coach is a serverless portfolio application for resume analysis, job matching, resume tailoring, and interview preparation.

## Platform status

The Platform V2 multi-site active-active program is **implemented and runtime-certified**.

- Active application sites: `us-east-1` and `us-west-2`
- DynamoDB MRSC witness: `us-east-2`
- Global API routing: Route 53 latency records with health checks
- Regional execution: API Gateway, API Lambda, outbox publisher, SQS, worker, document bucket
- Shared capabilities: Cognito identity and DynamoDB system of record
- Certification baseline: MR-014, completed July 22, 2026

The certification proved the both-sites-disabled guard, bidirectional routing isolation and restoration, authenticated survivor-region work, owner-region correctness, cross-region reads, durable worker backlog, idempotent duplicate submission, worker restoration, workflow completion, queue drain, and final multi-site reconciliation.

The multi-site program does **not** claim full production readiness. Cognito WAF, permanent operational alarms, dashboards, and synthetic monitoring remain optional production-hardening controls outside MR-015/MR-016.

## Documentation map

See [`docs/README.md`](docs/README.md) for the architecture, certification, operations, engineering, and historical-documentation index.

## Authoritative documentation

- `docs/architecture/platform-v2/PLATFORM_V2_ARCHITECTURE.md`
- `docs/architecture/platform-v2/MR-016_FINAL_ACCEPTANCE.md`
- `docs/certification/MR-014_MULTI_SITE_CERTIFICATION.md`
- `docs/operations/platform-v2/MULTI_SITE_OPERATIONS_RUNBOOK.md`
- `docs/engineering/MULTI_SITE_COMPLETION_PLAN.md`

## Validation

```bash
python -m compileall src tests tools
pytest -q
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate
terraform -chdir=infra test
./tools/validate_platform_v2_foundation.sh
```

Mutating multi-site certification remains explicitly approval-gated:

```bash
CONFIRM_MUTATION=YES \
EXECUTE_CHAOS=YES \
./tools/multi_site/mr014_chaos_validation.sh certify
```
