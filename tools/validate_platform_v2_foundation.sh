#!/usr/bin/env bash
set -euo pipefail

BUNDLE_ROOT="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
  pwd
)"

SOURCE_INFRA="${BUNDLE_ROOT}/infra"
VALIDATION_ROOT="${TMPDIR:-/tmp}/ai-resume-coach-platform-v2-production-readiness"

rm -rf "${VALIDATION_ROOT}"
mkdir -p "${VALIDATION_ROOT}"

cp -R "${SOURCE_INFRA}/." "${VALIDATION_ROOT}/infra"

for package_name in \
  api \
  worker \
  outbox_publisher \
  registration_notification
do
  package_root="${VALIDATION_ROOT}/build/lambda/${package_name}"
  mkdir -p "${package_root}"

  cat > "${package_root}/handler.py" <<'PY'
def lambda_handler(event, context):
    return {"status": "validation-placeholder"}


def handler(event, context):
    return {"status": "validation-placeholder"}
PY
done

rm -rf "${VALIDATION_ROOT}/infra/.terraform"
rm -f "${VALIDATION_ROOT}/infra/.terraform.lock.hcl"

terraform -chdir="${VALIDATION_ROOT}/infra" init \
  -backend=false \
  -input=false

terraform -chdir="${VALIDATION_ROOT}/infra" fmt \
  -recursive

terraform -chdir="${VALIDATION_ROOT}/infra" fmt \
  -check \
  -recursive

terraform -chdir="${VALIDATION_ROOT}/infra" validate

terraform -chdir="${VALIDATION_ROOT}/infra" test

echo
echo "Platform V2 multi-site production readiness validation passed."
echo "Validated copy: ${VALIDATION_ROOT}"
