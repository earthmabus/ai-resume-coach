import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "tools" / "resilience" / "dr_validation_report.py"
SPEC = importlib.util.spec_from_file_location("ms022_dr_report", REPORT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_report_fails_when_any_check_fails(tmp_path):
    checks = tmp_path / "checks.jsonl"
    checks.write_text(
        json.dumps({"name": "east_ready", "status": "PASS", "detail": "ok"})
        + "\n"
        + json.dumps({"name": "west_ready", "status": "FAIL", "detail": "down"})
        + "\n"
    )
    report = MODULE.build_report(MODULE.load_checks(checks), "assess")
    assert report["status"] == "FAIL"
    assert report["summary"] == {"total": 2, "passed": 1, "failed": 1}


def test_report_preserves_honest_dr_boundaries(tmp_path):
    checks = tmp_path / "checks.jsonl"
    checks.write_text(json.dumps({"name": "contracts", "status": "PASS", "detail": "ok"}) + "\n")
    report = MODULE.build_report(MODULE.load_checks(checks), "exercise")
    joined = " ".join(report["limitations"])
    assert "No Route 53 records" in joined
    assert "Cognito recovery is contract-validated" in joined
    assert "ownerRegion is not changed automatically" in joined


def test_live_validator_checks_both_sites_and_both_replication_directions():
    text = (ROOT / "tools" / "validate" / "disaster_recovery.sh").read_text()
    for token in (
        'probe_health "east_ready"',
        'probe_health "west_ready"',
        'probe_health "global_ready"',
        "exercise_replication east_to_west",
        "exercise_replication west_to_east",
        "confirm_mutation",
    ):
        assert token in text


def test_activation_does_not_offer_outage_injection():
    text = (ROOT / "tools" / "resilience" / "activate_disaster_recovery_validation.sh").read_text()
    assert "does not disable Route 53" in text
    assert "CONFIRM_MUTATION=YES" in text
    for forbidden in ("update-health-check", "change-resource-record-sets", "delete-function", "disable-rule"):
        assert forbidden not in text


def test_terraform_contract_names_unexercised_failover_boundaries():
    text = (ROOT / "infra" / "outputs.tf").read_text()
    assert 'mode' in text and '"CONTROL_PLANE_AND_BOUNDED_DATA_PATH"' in text
    assert "actual_outage_injection" in text and "= false" in text
    assert "identity_failover_exercised" in text and "= false" in text
    assert "processing_owner_transfer_exercised" in text


def test_documentation_has_operator_commands_and_evidence_boundary():
    text = (
        ROOT
        / "docs"
        / "architecture"
        / "platform-resilience"
        / "MS-022_DISASTER_RECOVERY_VALIDATION.md"
    ).read_text()
    assert "activate_disaster_recovery_validation.sh assess" in text
    assert "CONFIRM_MUTATION=YES" in text
    assert "not a destructive regional-outage exercise" in text
