#!/bin/bash

show_help() {
  cat <<'EOF'
Usage: tools/inspect/environment.sh [COMMAND] [OPTIONS]

Purpose:
  Inspect the runtime-validation environment and fail on missing prerequisites.

Environment variables:
  TFVARS_FILE
      Path to a complete tfvars profile. Compose with: tools/prepare/mr014_certification.sh compose

  SYNTHETIC_PDF
      Path to an approved synthetic PDF; verify with: test -f "$SYNTHETIC_PDF"

  AUTH_TOKEN
      Sensitive. Acquire with: source tools/prepare/auth.sh

Safety:
  --help performs no validation, file creation, AWS calls, or mutations.
EOF
}

case "${1:-}" in -h|--help) show_help; exit 0 ;; esac

test -f "$TFVARS_FILE" && echo "TFVARS_FILE OK"
test -f "$SYNTHETIC_PDF" && echo "SYNTHETIC_PDF OK"
test -n "$AUTH_TOKEN" && echo "AUTH_TOKEN OK"
