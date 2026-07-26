# Repository Document Index

> **Status:** Canonical
> **Audience:** All repository readers
> **Purpose:** Provide audience-based navigation and the complete inventory entry point
> **Owner:** Documentation Maintainers
> **Related documents:** [Documentation portal](README.md), [document mapping](DOCUMENT_MAPPING.md), [migration guide](MIGRATION_GUIDE.md)

## Primary publications

| Audience or question | Publication |
|---|---|
| Engineering leaders and hiring managers | [Executive documentation](executive/README.md) |
| Developers and architects | [Architecture publications](architecture/README.md) |
| Operators and incident responders | [Operations portal](operations/README.md) |
| Active-active and disaster recovery | [MVP2 disaster recovery](mvp2-disaster-recovery/README.md) |
| Validation and formal evidence | [Certification records](certification/README.md) |
| Contributors and reviewers | [Engineering documentation](engineering/README.md) |
| Product intent and direction | [Product documentation](product/README.md) |
| Repository and terminology reference | [Reference](reference/README.md) |
| Delivery chronology | [History](history/README.md) |
| Superseded packages and reviews | [Archive](archive/README.md) |

## Authority and lifecycle

Executable application tests, Terraform contract tests, and supported tooling take precedence over prose. Canonical publications explain current behavior; decisions explain why; runbooks explain how to operate; certification records prove named contracts; milestone records preserve delivery evidence; drafts and archives are non-authoritative.

The complete per-file inventory, classification, destination, rationale, and preservation result is [DOCUMENT_MAPPING.md](DOCUMENT_MAPPING.md). It inventories all repository Markdown, including root guidance and portfolio material.

## Maintenance

Run `./tools/docs/validate_documentation.sh` after documentation changes. The validator checks local links, canonical metadata, title collisions, mapping coverage, archive-primary links, and shell syntax for documentation scripts.
