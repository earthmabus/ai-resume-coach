#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

show_help() {
  cat <<'EOF'
Usage: ./tools/resilience/platform_readiness.sh [--json] [--report PATH]

Produces the lightweight MS-017 resilience assessment from Terraform outputs.
This command is read-only and makes no AWS mutations.
EOF
}

case "${1:-}" in
  -h|--help) show_help; exit 0 ;;
esac

command -v terraform >/dev/null 2>&1 || { echo "terraform is required" >&2; exit 2; }
command -v python >/dev/null 2>&1 || { echo "python is required" >&2; exit 2; }

exec python "$ROOT_DIR/tools/resilience/platform_readiness.py" \
  --infra-dir "$ROOT_DIR/infra" \
  "$@"
