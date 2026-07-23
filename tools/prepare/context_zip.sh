#!/usr/bin/env bash
set -euo pipefail

cd ~/Projects/ai-resume-coach

show_help() {
  cat <<'EOF'
Usage: tools/prepare/context_zip.sh [COMMAND] [OPTIONS]

Purpose:
  Create a sanitized repository context ZIP for review.

Environment variables:
  HOME
      Set explicitly for the target environment.

Safety:
  --help performs no validation, file creation, AWS calls, or mutations.
EOF
}

case "${1:-}" in -h|--help) show_help; exit 0 ;; esac
rm -rf ~/Downloads/repo-context.zip

rm -rf /tmp/repo-context
mkdir -p /tmp/repo-context


rsync -a \
  --exclude='.git/' \
  --exclude='.terraform/' \
  --exclude='.pytest_cache/' \
  --exclude='__pycache__/' \
  --exclude='.mypy_cache/' \
  --exclude='.ruff_cache/' \
  --exclude='.venv/' \
  --exclude='venv/' \
  --exclude='/build/' \
  --exclude='dist/' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='*.tfstate' \
  --exclude='*.tfstate.*' \
  --exclude='.DS_Store' \
  ./ \
  /tmp/repo-context/

cd /tmp/repo-context

zip -qr ~/Downloads/repo-context.zip .
