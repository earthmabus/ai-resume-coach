#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEFAULT_OUTPUT="${HOME}/Downloads/repo-context.zip"
OUTPUT_PATH="$DEFAULT_OUTPUT"

show_help() {
  cat <<'HELP'
Usage: tools/prepare/context_zip.sh [--output PATH]

Create a sanitized ZIP of the full repository for review.

Options:
  -o, --output PATH  Write the ZIP to PATH.
                     Default: ~/Downloads/repo-context.zip
  -h, --help         Show this help message and exit.

The archive excludes Git history, local Terraform state/cache, generated
artifacts, virtual environments, test caches, runtime evidence, local secrets,
and other machine-specific files. A small repository manifest is included at
.context/repository-manifest.txt.
HELP
}

while (($# > 0)); do
  case "$1" in
    -o|--output)
      if (($# < 2)); then
        echo "ERROR: $1 requires a path." >&2
        exit 2
      fi
      OUTPUT_PATH="$2"
      shift 2
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      echo >&2
      show_help >&2
      exit 2
      ;;
  esac
done

for command_name in rsync zip; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $command_name" >&2
    exit 1
  fi
done

case "$OUTPUT_PATH" in
  ~/*) OUTPUT_PATH="${HOME}/${OUTPUT_PATH#~/}" ;;
esac
OUTPUT_PATH="$(realpath -m "$OUTPUT_PATH")"
mkdir -p "$(dirname "$OUTPUT_PATH")"

STAGING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ai-resume-coach-context.XXXXXX")"
cleanup() {
  rm -rf "$STAGING_DIR"
}
trap cleanup EXIT

cd "$ROOT_DIR"

# Include example configuration before excluding local configuration files.
rsync -a \
  --exclude='.git/' \
  --exclude='.terraform/' \
  --exclude='**/.terraform/' \
  --exclude='.pytest_cache/' \
  --exclude='**/.pytest_cache/' \
  --exclude='__pycache__/' \
  --exclude='**/__pycache__/' \
  --exclude='.mypy_cache/' \
  --exclude='.ruff_cache/' \
  --exclude='.venv/' \
  --exclude='venv/' \
  --exclude='**/node_modules/' \
  --exclude='/build/' \
  --exclude='/dist/' \
  --exclude='/debug/' \
  --exclude='/evidence/' \
  --exclude='htmlcov/' \
  --exclude='.coverage' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='*.tfstate' \
  --exclude='*.tfstate.*' \
  --exclude='*.tfplan' \
  --exclude='tfplan*' \
  --exclude='tfdestroy*' \
  --exclude='*.zip' \
  --exclude='*.log' \
  --include='*.tfvars.example' \
  --exclude='*.tfvars' \
  --include='.env.example' \
  --include='*.env.example' \
  --exclude='.env' \
  --exclude='*.env' \
  --exclude='*.pem' \
  --exclude='*.key' \
  --exclude='*.p12' \
  --exclude='*.pfx' \
  --exclude='credentials' \
  --exclude='frontend/config.js' \
  --exclude='.DS_Store' \
  --exclude='.idea/' \
  --exclude='.vscode/' \
  ./ \
  "$STAGING_DIR/"

mkdir -p "$STAGING_DIR/.context"
MANIFEST_PATH="$STAGING_DIR/.context/repository-manifest.txt"
{
  echo "Repository Context Manifest"
  echo "==========================="
  echo "Generated UTC: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "Repository: $(basename "$ROOT_DIR")"

  if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Branch: $(git branch --show-current 2>/dev/null || echo unknown)"
    echo "Commit: $(git rev-parse HEAD 2>/dev/null || echo unknown)"
    if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
      echo "Working tree: modified"
    else
      echo "Working tree: clean"
    fi
  else
    echo "Git metadata: unavailable"
  fi

  echo "Python: $(python --version 2>&1 || echo unavailable)"
  echo "Terraform: $(terraform version -json 2>/dev/null | python -c 'import json,sys; print(json.load(sys.stdin).get("terraform_version", "unknown"))' 2>/dev/null || echo unavailable)"
  echo
  echo "Sanitization: local state, caches, build output, runtime evidence,"
  echo "generated archives, local tfvars/env files, and common key files excluded."
} > "$MANIFEST_PATH"

rm -f "$OUTPUT_PATH"
(
  cd "$STAGING_DIR"
  zip -qr "$OUTPUT_PATH" .
)

FILE_COUNT="$(unzip -Z1 "$OUTPUT_PATH" | wc -l | tr -d ' ')"
ARCHIVE_SIZE="$(du -h "$OUTPUT_PATH" | awk '{print $1}')"

echo "Repository context created successfully."
echo "Path: $OUTPUT_PATH"
echo "Files: $FILE_COUNT"
echo "Size: $ARCHIVE_SIZE"
