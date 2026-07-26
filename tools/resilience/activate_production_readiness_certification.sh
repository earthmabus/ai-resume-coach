#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/tools/lib/multi_site.sh"

show_help() {
  cat <<'HELP'
Usage: tools/resilience/activate_production_readiness_certification.sh {assess|certify} [--profile PROFILE]

Profiles:
  development      Local or developer-owned cloud environment.
  integration      Shared integration/testing environment.
  pre-production   Staging/UAT environment with production-equivalent resilience.
  production       Internet-facing production environment.

assess   Run the read-only MS-024A profile-aware assessment and generate
         candidate JSON, text, and Markdown evidence.
certify  Run the same assessment and publish a profile-specific Markdown record
         under docs/certification only when every profile-blocking control passes.

The default profile is pre-production. No AWS mutations are performed.
HELP
}

command="${1:-assess}"
if [[ "$command" == "-h" || "$command" == "--help" ]]; then
  show_help
  exit 0
fi
shift || true

profile="${CERTIFICATION_PROFILE:-pre-production}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      [[ $# -ge 2 ]] || { echo "--profile requires a value" >&2; exit 2; }
      profile="$2"
      shift 2
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      show_help >&2
      exit 2
      ;;
  esac
done

profile="${profile,,}"
profile="${profile//_/-}"
case "$profile" in
  development|integration|pre-production|production) ;;
  *) echo "Invalid certification profile: $profile" >&2; show_help >&2; exit 2 ;;
esac
export CERTIFICATION_PROFILE="$profile"

case "$command" in
  assess)
    exec "$ROOT_DIR/tools/validate/production_readiness_certification.sh"
    ;;
  certify)
    new_evidence_dir "ms024a-certify-${profile}"
    export EVIDENCE_DIR_OVERRIDE="$EVIDENCE_DIR"
    set +e
    "$ROOT_DIR/tools/validate/production_readiness_certification.sh"
    status=$?
    set -e
    candidate="$EVIDENCE_DIR/MS-024A_PROFILE_READINESS_CERTIFICATION.md"
    if [[ "$status" -ne 0 ]]; then
      echo "MS-024A $profile certification was not published because required profile controls failed." >&2
      echo "Candidate: $candidate" >&2
      exit "$status"
    fi
    profile_file="${profile//-/_}"
    profile_file="${profile_file^^}"
    destination="$ROOT_DIR/docs/certification/MS-024A_${profile_file}_READINESS_CERTIFICATION.md"
    cp "$candidate" "$destination"
    record "PASSED: MS-024A $profile readiness certification published"
    printf 'Certification: %s\nEvidence: %s\n' "$destination" "$EVIDENCE_DIR"
    ;;
  *) show_help >&2; exit 2 ;;
esac
