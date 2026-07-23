#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
usage(){ cat <<'HELP'
Usage: tools/inspect/run.sh <command> [args]
Commands:
  environment           Inspect required environment and AWS identity.
  jwt                    Inspect JWT claims.
  evidence               Collect/read multi-site evidence.
HELP
}
case "${1:-}" in
  -h|--help|'') usage; [[ -n "${1:-}" ]] || exit 2; exit 0 ;;
  environment) shift; exec "$ROOT_DIR/tools/inspect/environment.sh" "$@" ;;
  jwt) shift; exec python "$ROOT_DIR/tools/inspect/jwt_claims.py" "$@" ;;
  evidence) shift; exec "$ROOT_DIR/tools/inspect/multi_site_evidence.sh" "$@" ;;
  *) echo "Unknown inspect command: $1" >&2; usage >&2; exit 2 ;;
esac
