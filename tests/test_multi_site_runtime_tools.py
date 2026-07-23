from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.inspect.jwt_claims import claim_values, decode_payload, groups

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tools/validate/mr009d3b_runtime.sh"


def _jwt(payload: dict) -> str:
    import base64
    raw = json.dumps(payload, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return f"header.{encoded}.signature"


def test_jwt_inspector_decodes_only_safe_summary_fields(tmp_path):
    token = _jwt({
        "sub": "user-1",
        "email": "private@example.com",
        "cognito:groups": ["synthetic-runtime-validation"],
        "exp": 123,
    })
    output = tmp_path / "claims.json"
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/inspect/jwt_claims.py"), "--token", token,
         "--require-group", "synthetic-runtime-validation", "--output", str(output)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    summary = json.loads(output.read_text())
    assert summary["groups"] == ["synthetic-runtime-validation"]
    assert "email" not in summary
    assert token not in output.read_text()


def test_jwt_inspector_rejects_missing_required_group(tmp_path):
    token = _jwt({"sub": "user-1", "cognito:groups": ["users"]})
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/inspect/jwt_claims.py"), "--token", token,
         "--require-group", "synthetic-runtime-validation"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 3
    assert "required group" in result.stderr


def test_claim_parser_matches_runtime_supported_shapes():
    assert claim_values('["users", "synthetic-runtime-validation"]') == {
        "users", "synthetic-runtime-validation"
    }
    assert groups({"groups": "[synthetic-runtime-validation]"}) == {
        "synthetic-runtime-validation"
    }


def test_runtime_harness_local_flow_has_no_override_and_remote_flow_does():
    text = HARNESS.read_text()
    assert 'run_flow east-local "$EAST_API"' in text
    assert 'run_flow east-to-west "$EAST_API" "${WEST_REGION:-us-west-2}"' in text
    assert 'placement_headers+=(\n      -H "X-Validation-Owner-Region: $owner"' in text
    upload_block, analysis_block = text.split('http_request "$name submit resume analysis"', 1)
    assert 'X-Validation-Owner-Region' not in upload_block.split('http_request "$name create upload URL"', 1)[1]
    assert '"${placement_headers[@]}"' in analysis_block


def test_runtime_tfvars_example_is_not_automatically_loaded_by_terraform():
    infra = ROOT / "infra"
    assert (infra / "runtime-validation.tfvars.example").is_file()
    assert not (infra / "runtime-validation.tfvars").exists()
    assert not list(infra.glob("*runtime-validation*.auto.tfvars"))
