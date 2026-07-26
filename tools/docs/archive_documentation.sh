#!/usr/bin/env bash
set -euo pipefail

mode="dry-run"
case "${1:---dry-run}" in
  --dry-run) ;;
  --apply) mode="apply" ;;
  *)
    echo "Usage: $0 [--dry-run|--apply]" >&2
    exit 2
    ;;
esac

repository_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$repository_root" || "$PWD" != "$repository_root" ]]; then
  echo "Refusing to run: execute this script from the repository root." >&2
  exit 1
fi

sources=(
  "docs/operations/platform-v2/MR-009D_DEPLOYMENT_REPORT.md"
  "docs/operations/platform-v2/MR-009D_RUNTIME_DISCOVERY_REPORT.md"
  "docs/operations/platform-v2/MR-009D_RUNTIME_EVIDENCE_REPORT.md"
  "docs/operations/platform-v2/MR-009D_RUNTIME_VALIDATION_PLAN.md"
  "docs/operations/platform-v2/MR-009D4_RUNTIME_VALIDATION_PLAN.md"
)
destinations=(
  "docs/archive/operations/MR-009D_DEPLOYMENT_REPORT.md"
  "docs/archive/operations/MR-009D_RUNTIME_DISCOVERY_REPORT.md"
  "docs/archive/operations/MR-009D_RUNTIME_EVIDENCE_REPORT.md"
  "docs/archive/operations/MR-009D_RUNTIME_VALIDATION_PLAN.md"
  "docs/archive/operations/MR-009D4_RUNTIME_VALIDATION_PLAN.md"
)

echo "Documentation archive mode: $mode"
for index in "${!sources[@]}"; do
  source_path="${sources[$index]}"
  destination_path="${destinations[$index]}"

  if [[ ! -e "$source_path" ]]; then
    echo "SKIP missing: $source_path"
    continue
  fi
  if ! git ls-files --error-unmatch -- "$source_path" >/dev/null 2>&1; then
    echo "Refusing to archive untracked source: $source_path" >&2
    exit 1
  fi
  if [[ -e "$destination_path" ]]; then
    echo "Refusing to overwrite destination: $destination_path" >&2
    exit 1
  fi

  echo "MOVE $source_path -> $destination_path"
  if [[ "$mode" == "apply" ]]; then
    mkdir -p "$(dirname "$destination_path")"
    git mv -- "$source_path" "$destination_path"
  fi
done

if [[ "$mode" == "dry-run" ]]; then
  echo "Dry run only; no files were moved."
fi
