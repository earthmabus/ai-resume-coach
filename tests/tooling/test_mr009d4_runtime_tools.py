from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.inspect.jwt_claims import remaining_lifetime

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tools/validate/failover_runtime.sh"


def _jwt(payload: dict) -> str:
    import base64
    raw = json.dumps(payload, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return f"header.{encoded}.signature"


def test_remaining_lifetime_uses_expiration_timestamp():
    assert remaining_lifetime({"exp": 2_000}, now=1_250) == 750
    assert remaining_lifetime({}, now=1_250) is None


def test_jwt_inspector_rejects_expired_or_short_lived_token(tmp_path):
    token = _jwt({"sub": "user-1", "token_use": "id", "exp": 1})
    output = tmp_path / "claims.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/inspect/jwt_claims.py"),
            "--token", token,
            "--require-token-use", "id",
            "--min-remaining-seconds", "900",
            "--output", str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 6
    assert "remaining lifetime" in result.stderr
    summary = json.loads(output.read_text())
    assert summary["tokenUse"] == "id"
    assert summary["remainingLifetimeSeconds"] < 0
    assert token not in output.read_text()


def test_jwt_inspector_rejects_wrong_token_use(tmp_path):
    import time
    token = _jwt({"sub": "user-1", "token_use": "access", "exp": int(time.time()) + 3600})
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/inspect/jwt_claims.py"),
            "--token", token,
            "--require-token-use", "id",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 4
    assert "token_use must be id" in result.stderr


def test_mr009d4_harness_has_bidirectional_isolation_and_restoration():
    text = HARNESS.read_text()
    assert "apply_routing isolate-east '{east=false,west=true}'" in text
    assert "apply_routing isolate-west '{east=true,west=false}'" in text
    assert "restore_routing restore-east" in text
    assert "restore_routing restore-west" in text
    assert "trap restore_both_sites EXIT INT TERM" in text
    assert "site_routing_enabled={east=true,west=true}" in text


def test_mr009d4_harness_validates_survivor_through_global_and_direct_apis():
    text = HARNESS.read_text()
    assert 'wait_for_global_region "${WEST_REGION:-us-west-2}" east-isolated' in text
    assert 'wait_for_global_region "${EAST_REGION:-us-east-1}" west-isolated' in text
    assert 'submit_survivor_flow east-isolated "${WEST_REGION:-us-west-2}" "$WEST_API"' in text
    assert 'submit_survivor_flow west-isolated "${EAST_REGION:-us-east-1}" "$EAST_API"' in text
    assert 'read analysis through global API' in text
    assert 'read analysis through surviving direct API' in text
    assert "X-Validation-Owner-Region" not in text


def test_mr009d4_requires_explicit_mutation_authorization_and_tfvars():
    text = HARNESS.read_text()
    assert 'EXECUTE_FAILOVER:-NO' in text
    assert "confirm_mutation" in text
    assert "require_env TFVARS_FILE" in text
    assert '-var-file="$TFVARS_FILE"' in text
    assert "runtime-validation.auto.tfvars" not in text


def test_mr009d4_declares_correlation_id_before_request_id():
    text = HARNESS.read_text()

    corr_declaration = (
        'local corr="mr009d4-${label}-$(date -u +%s)"'
    )
    request_declaration = 'local request_id="${corr}-request"'

    assert corr_declaration in text
    assert request_declaration in text
    assert text.index(corr_declaration) < text.index(request_declaration)

    assert (
        'local corr="mr009d4-${label}-$(date -u +%s)" '
        'request_id="${corr}-request"'
    ) not in text


def test_mr009d4_rejects_non_routing_terraform_changes():
    text = HARNESS.read_text()

    assert "validate_routing_only_plan" in text
    assert 'terraform -chdir="$INFRA_DIR" show -json "$plan_file"' in text
    assert 'module.global_edge.aws_route53_record.east_api_a[0]' in text
    assert 'module.global_edge.aws_route53_record.west_api_a[0]' in text
    assert "plan contains non-routing resource changes" in text
    assert "Refusing apply; reconcile Terraform drift or input variables first" in text
    assert 'validate_routing_only_plan "$label"' in text


def test_mr009d4_validates_safety_restore_plan_before_apply():
    text = HARNESS.read_text()

    validation = "validate_routing_only_plan safety-restore"
    apply_command = (
        'terraform -chdir="$INFRA_DIR" apply -input=false '
        '"$EVIDENCE_DIR/safety-restore.tfplan"'
    )

    assert validation in text
    assert apply_command in text
    assert text.index(validation) < text.index(apply_command)


def test_mr009d4_aligns_routing_plans_to_deployed_runtime_inputs():
    harness = HARNESS.read_text()
    common = (ROOT / "tools/lib/multi_site.sh").read_text()

    assert "prepare_deployed_runtime_alignment" in common
    assert "get-function-configuration" in common
    assert "DEPLOYMENT_ID" in common
    assert "ANALYSIS_PROVIDER" in common
    assert "Deployed DEPLOYMENT_ID values are missing or inconsistent" in common
    assert "Deployed ANALYSIS_PROVIDER values are missing or inconsistent" in common
    assert "TERRAFORM_RUNTIME_ALIGNMENT_ARGS" in common

    assert "prepare_deployed_runtime_alignment" in harness
    assert harness.count('"${TERRAFORM_RUNTIME_ALIGNMENT_ARGS[@]}"') == 2
    assert "Terraform runtime inputs aligned to deployed Lambda configuration" in harness
