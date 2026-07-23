#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
usage(){ cat <<'HELP'
Usage: tools/operations/run.sh <command> [args]
Commands:
  failover-recovery      Perform an explicitly approved failover/recovery operation.
  replay-outbox          Replay a permanently failed outbox event.
  replay-example         Show the replay command example.
HELP
}
case "${1:-}" in
  -h|--help|'') usage; [[ -n "${1:-}" ]] || exit 2; exit 0 ;;
  failover-recovery) shift; exec "$ROOT_DIR/tools/operations/failover_recovery.sh" "$@" ;;
  replay-outbox) shift; exec python "$ROOT_DIR/tools/operations/replay_outbox.py" "$@" ;;
  replay-example) shift; exec "$ROOT_DIR/tools/operations/replay_failed_permanent.sh" "$@" ;;
  *) echo "Unknown operations command: $1" >&2; usage >&2; exit 2 ;;
esac
