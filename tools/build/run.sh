#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
usage(){ cat <<'HELP'
Usage: tools/build/run.sh <command> [args]
Commands:
  lambda-packages       Build Lambda deployment packages.
  pdf-layer             Build the PDF dependency layer.
HELP
}
case "${1:-}" in
  -h|--help|'') usage; [[ -n "${1:-}" ]] || exit 2; exit 0 ;;
  lambda-packages) shift; exec python "$ROOT_DIR/tools/build/lambda_packages.py" "$@" ;;
  pdf-layer) shift; exec python "$ROOT_DIR/tools/build/pdf_dependency_layer.py" "$@" ;;
  *) echo "Unknown build command: $1" >&2; usage >&2; exit 2 ;;
esac
