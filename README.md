# AI Resume Coach

AI Resume Coach is a serverless application for resume analysis, job matching, resume tailoring, and interview preparation.

## Platform status

The Platform V2 multi-site active-active program is **implemented and runtime-certified**.

- Active application sites: `us-east-1` and `us-west-2`
- DynamoDB MRSC witness: `us-east-2`
- Global API routing: Route 53 latency records with health checks
- Regional execution: API Gateway, API Lambda, outbox publisher, SQS, worker, and document bucket
- Shared capabilities: Cognito identity and DynamoDB system of record
- Certification baseline: MR-014, completed July 22, 2026

The certification proved the both-sites-disabled guard, bidirectional routing isolation and restoration, authenticated survivor-region work, owner-region correctness, cross-region reads, durable worker backlog, idempotent duplicate submission, worker restoration, workflow completion, queue drain, and final multi-site reconciliation.

The multi-site program does **not** claim full production readiness. Cognito WAF, permanent operational alarms, dashboards, and synthetic monitoring remain optional production-hardening controls outside MR-015/MR-016.

## Repository map

- `src/` — application, worker, and shared domain/runtime code
- `frontend/` — static browser application
- `infra/` — Terraform composition, modules, and contract tests
- `tests/` — application and tooling tests
- `tools/` — operator tooling grouped by intent
- `docs/` — architecture, engineering, operations, certification, and history

See [`docs/architecture/REPOSITORY_STRUCTURE.md`](docs/architecture/REPOSITORY_STRUCTURE.md) for ownership and placement rules.

## Getting started

Prerequisites:

- Python 3.12 or compatible project runtime
- Terraform matching `infra/versions.tf`
- AWS CLI configured for the intended account
- `zip`, `rsync`, and standard Unix shell tools

Clone and validate:

```bash
git clone https://github.com/earthmabus/ai-resume-coach.git
cd ai-resume-coach

python -m compileall src tests tools
pytest -q
./tools/validate/run.sh terraform
```

Prepare a Terraform plan:

```bash
export TF_VAR_deployment_id="$(git rev-parse HEAD)"
export TF_VAR_registration_notification_email="you@example.com"
./tools/prepare/run.sh terraform-plan
```

Inspect available operator commands:

```bash
./tools/build/run.sh --help
./tools/prepare/run.sh --help
./tools/inspect/run.sh --help
./tools/validate/run.sh --help
./tools/operations/run.sh --help
```

## Documentation map

See [`docs/README.md`](docs/README.md) for the architecture, certification, operations, engineering, and historical-documentation index.

Architecture diagram portfolio: [`docs/mvp2-disaster-recovery/README.md`](docs/mvp2-disaster-recovery/README.md).

Director portfolio: [`portfolio/README.md`](portfolio/README.md).

Production operating model and KPI catalog: [`docs/operations/production/README.md`](docs/operations/production/README.md).

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
./tools/validate/run.sh terraform
./tools/validate/run.sh platform
```

Mutating multi-site certification remains explicitly approval-gated:

```bash
CONFIRM_MUTATION=YES \
EXECUTE_CHAOS=YES \
./tools/validate/run.sh chaos certify
```
