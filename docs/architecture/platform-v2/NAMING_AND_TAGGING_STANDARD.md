# Naming and Tagging Standard

## Regional names

Format:

```text
<project>-<environment>-<region-code>-<capability>
```

Examples:

```text
ai-resume-coach-dev-use1-api
ai-resume-coach-dev-usw2-worker
ai-resume-coach-dev-use1-processing
ai-resume-coach-dev-usw2-documents
```

Region codes:

- `us-east-1` → `use1`
- `us-west-2` → `usw2`
- `us-east-2` → `use2`

## Shared names

Shared resources omit a regional code, such as `ai-resume-coach-dev-users` and `ai-resume-coach-dev-frontend`.

## Required tags

- `Project`
- `Environment`
- `ManagedBy`
- `ArchitectureVersion=platform-v2`
- `Scope=regional|global`
- `RegionRole=active|shared|witness`

Application records continue to store full AWS Region names and full deployment IDs.
