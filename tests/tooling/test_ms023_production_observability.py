import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "tools" / "resilience" / "operations_report.py"
SPEC = importlib.util.spec_from_file_location("ms023_operations_report", REPORT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_report_fails_on_failed_check(tmp_path):
    checks = tmp_path / "checks.jsonl"
    checks.write_text(
        json.dumps({"name": "dashboard", "status": "PASS", "detail": "ok"}) + "\n"
        + json.dumps({"name": "canary", "status": "FAIL", "detail": "stopped"}) + "\n"
    )
    report = MODULE.build_report(MODULE.load_checks(checks))
    assert report["status"] == "FAIL"
    assert report["summary"] == {"total": 2, "passed": 1, "warnings": 0, "failed": 1}


def test_report_allows_notification_warning(tmp_path):
    checks = tmp_path / "checks.jsonl"
    checks.write_text(
        json.dumps({"name": "alarms", "status": "PASS", "detail": "ok"}) + "\n"
        + json.dumps({"name": "notifications", "status": "WARN", "detail": "none"}) + "\n"
    )
    report = MODULE.build_report(MODULE.load_checks(checks))
    assert report["status"] == "PASS"
    assert report["summary"]["warnings"] == 1


def test_activation_preserves_prior_resilience_controls():
    text = (ROOT / "tools" / "resilience" / "activate_production_observability.sh").read_text()
    for token in (
        "enable_cognito_recovery=true",
        "enable_document_replication=true",
        "enable_observability_dashboard=true",
        "enable_operational_alarms=true",
        "enable_synthetic_monitoring=true",
        "CONFIRM_MUTATION=YES",
    ):
        assert token in text


def test_validator_checks_dashboard_alarms_and_three_canaries():
    text = (ROOT / "tools" / "validate" / "production_observability.sh").read_text()
    for token in (
        "get-dashboard",
        "validate_regional_alarms east us-east-1",
        "validate_regional_alarms west us-west-2",
        "east-alarms.json",
        "west-alarms.json",
        "validate_canary global us-east-1",
        "validate_canary east us-east-1",
        "validate_canary west us-west-2",
    ):
        assert token in text


def test_synthetic_checks_all_public_health_paths():
    text = (ROOT / "infra" / "synthetics" / "nodejs" / "node_modules" / "health.js").read_text()
    for path in ("/health", "/health/live", "/health/ready"):
        assert path in text
    assert "executeHttpStep" in text
    assert "API_ENDPOINT" in text


def test_terraform_adds_lambda_throttle_alarms_and_global_canary():
    regional = (ROOT / "infra" / "modules" / "regional_application" / "observability.tf").read_text()
    root_observability = (ROOT / "infra" / "observability.tf").read_text()
    assert 'resource "aws_cloudwatch_metric_alarm" "lambda_throttles"' in regional
    assert 'metric_name = "Throttles"' in regional
    assert 'resource "aws_synthetics_canary" "global"' in root_observability


def test_documentation_calls_out_cost_and_notification_boundaries():
    text = (
        ROOT
        / "docs"
        / "architecture"
        / "platform-resilience"
        / "MS-023_PRODUCTION_OBSERVABILITY.md"
    ).read_text()
    assert "ongoing AWS charges" in text
    assert "OBSERVABILITY_ALARM_ACTIONS" in text
    assert "does not authenticate" in text
