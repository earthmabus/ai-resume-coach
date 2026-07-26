# AI Resume Coach

AI Resume Coach is an AI-enabled career development platform and enterprise cloud engineering reference implementation. It helps users establish a target career, analyze resume evidence, tailor resumes, and compare resumes with job opportunities while demonstrating secure, observable, multi-region serverless architecture on AWS.

The repository contains the browser application, Python services, Terraform infrastructure, automated tests, operational tooling, certification evidence, and the architecture record for the platform.

## Platform at a Glance

The current platform combines:

- AI-assisted resume analysis
- Target-career management
- Resume tailoring
- Job matching
- Secure user authentication
- Serverless regional APIs and workers
- Multi-site active-active operation in `us-east-1` and `us-west-2`
- DynamoDB multi-Region strong consistency with a witness in `us-east-2`
- Regional document ownership and replication
- Transactional outbox and idempotency controls
- Explicit work ownership and processing state
- Global API routing and regional health classification
- Structured logging, dashboards, alarms, and synthetic monitoring
- Disaster recovery validation and readiness certification profiles

The platform is designed to demonstrate that AI-enabled product development and enterprise operational discipline can coexist without introducing unnecessary infrastructure complexity.

## Product Journey

A typical user journey is:

1. Sign in securely.
2. Define a target career.
3. Upload or select resume evidence.
4. Request resume analysis.
5. Review recommendations.
6. Tailor the resume for a role.
7. Compare the resume with job opportunities.

The architecture separates those product experiences from reusable platform capabilities such as identity, request context, persistence, asynchronous processing, observability, and disaster recovery.

## Architecture Overview

The platform is organized into the following layers:

| Layer | Responsibility |
|---|---|
| Browser application | Static user experience and authenticated client interactions |
| Global ingress | Global API routing, edge controls, and regional endpoint selection |
| Regional application | API Gateway, Lambda APIs, workers, queues, and regional storage |
| Shared data | Multi-Region strongly consistent DynamoDB state |
| Identity | Cognito authentication and regional identity recovery capabilities |
| AI providers | Provider abstractions used by resume and job-matching workflows |
| Operations | Validation, monitoring, recovery, certification, and evidence tooling |

The two active application regions are peers. Durable state records the authoritative owner of work independently from the region currently executing code. This allows the system to preserve business semantics during routing changes and regional disruption.

For the implemented architecture and its accepted boundaries, begin with:

- [Executive summary](docs/executive/EXECUTIVE_SUMMARY.md)
- [Canonical architecture publications](docs/architecture/README.md)
- [Multi-site disaster-recovery publication](docs/mvp2-disaster-recovery/README.md)
- [Final multi-site acceptance](docs/architecture/platform-v2/MR-016_FINAL_ACCEPTANCE.md)

## Repository Structure

```text
frontend/       Static browser application
src/            Python application, domain, Lambda, and worker code
infra/          Terraform composition, modules, examples, and contract tests
tests/          Application, architecture, repository, and tooling tests
tools/          Build, preparation, inspection, validation, and operations tools
docs/           Architecture, operations, engineering, certification, and history
portfolio/      Portfolio-oriented presentation material
```

The authoritative repository organization is documented in [Repository Structure](docs/architecture/REPOSITORY_STRUCTURE.md), and every Markdown document is classified in the [Document Mapping](docs/DOCUMENT_MAPPING.md).

## Documentation

The documentation portal is [docs/README.md](docs/README.md).

Recommended starting points:

| Goal | Start here |
|---|---|
| Understand the product and platform | [Executive Summary](docs/executive/EXECUTIVE_SUMMARY.md) |
| Understand the implemented architecture | [Architecture Publications](docs/architecture/README.md) |
| Review the active-active design visually | [Multi-Site Architecture Diagram Portfolio](docs/mvp2-disaster-recovery/README.md) |
| Operate the platform | [Operations Portal](docs/operations/README.md) |
| Review production operating expectations | [Production Operations](docs/operations/production/README.md) |
| Review certification evidence | [Certification Records](docs/certification/README.md) |
| Contribute safely | [Repository Guidance](AGENTS.md) and [Validation Contract](docs/engineering/VALIDATION_CONTRACT.md) |

## Current Readiness

The multi-site platform has completed final architectural acceptance and controlled failure certification. The repository also contains production observability controls and environment-specific readiness certification profiles.

The current pre-production certification record is:

- [MS-024A Pre-Production Readiness Certification](docs/certification/MS-024A_PRE_PRODUCTION_READINESS_CERTIFICATION.md)

Production certification remains intentionally stricter than architectural completion. Production-only controls, including configured alarm notification actions and required protective controls, must be present before the production profile can pass.

## Development and Validation

Repository guidance is defined in [AGENTS.md](AGENTS.md). The minimum validation contract for relevant changes is:

```bash
python -m compileall src tests
pytest -q tests

cd infra
terraform fmt -recursive -check
terraform validate
cd ..

./tools/validate/platform_v2_foundation.sh
git diff --check
```

Run focused tests first, then the full suite. Infrastructure deployment, `terraform apply`, commits, and other mutating operations should be performed only when explicitly intended.

## Architecture Principles

The platform follows several durable principles:

- Preserve clear product and platform boundaries.
- Prefer managed cloud services and small serverless components.
- Treat security, observability, and recovery as architecture, not add-ons.
- Keep request identity and correlation available across asynchronous boundaries.
- Keep work ownership explicit and separate from runtime placement.
- Use idempotency and transactional persistence to make retries safe.
- Automate validation instead of relying on undocumented operator knowledge.
- Preserve accepted architecture decisions unless a change explicitly reopens them.
- Avoid adding paid services or operational complexity without a demonstrated need.

## Portfolio Context

This project also serves as a director-level engineering portfolio demonstrating:

- cloud and solution architecture
- software engineering leadership
- cybersecurity-conscious design
- disaster recovery and operational governance
- Infrastructure as Code
- AI-assisted engineering practices
- incremental delivery with formal acceptance and certification

Portfolio resources are available under [portfolio/](portfolio/README.md).

## Project Status

The repository is actively maintained. Current documentation is authoritative unless a document is explicitly marked as historical, archived, a draft, or an implementation package.

Historical milestone documents remain valuable for traceability, but current platform behavior should be verified against executable tests, Terraform contracts, current architecture documentation, and supported operational tooling.
