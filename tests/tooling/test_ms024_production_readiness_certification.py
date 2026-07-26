import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "tools" / "resilience" / "production_readiness_certification.py"
SPEC = importlib.util.spec_from_file_location("ms024a_certification", REPORT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def check(name: str, category: str, status: str, detail: str = "detail"):
    return MODULE.Check(name=name, category=category, status=status, detail=detail)


def test_preproduction_profile_certifies_with_accepted_warnings():
    report = MODULE.build_report(
        [check("routing", "Reliability", "PASS"), check("waf", "Security", "WARN", "WAF recommended")],
        "deployment-1",
        "pre-production",
    )
    assert report["status"] == "PRE_PRODUCTION_CERTIFIED"
    assert report["profileReady"] is True
    assert report["productionReady"] is False
    assert report["hasExceptions"] is True


def test_production_profile_is_not_certified_when_required_control_fails():
    report = MODULE.build_report(
        [check("routing", "Reliability", "PASS"), check("waf", "Security", "FAIL", "WAF missing")],
        "deployment-1",
        "production",
    )
    assert report["status"] == "NOT_CERTIFIED"
    assert report["profileReady"] is False
    assert report["productionReady"] is False
    assert report["blockers"] == ["WAF missing"]


def test_production_profile_certifies_when_every_check_passes():
    report = MODULE.build_report([check("routing", "Reliability", "PASS")], "deployment-1", "production")
    assert report["status"] == "PRODUCTION_CERTIFIED"
    assert report["profileReady"] is True
    assert report["productionReady"] is True


def test_production_profile_can_record_nonblocking_exception():
    report = MODULE.build_report(
        [check("routing", "Reliability", "PASS"), check("note", "Governance", "WARN")],
        "deployment-1",
        "production",
    )
    assert report["status"] == "PRODUCTION_CERTIFIED_WITH_EXCEPTIONS"
    assert report["productionReady"] is True


@pytest.mark.parametrize("profile", ["development", "integration", "pre-production", "production", "PRE_PRODUCTION"])
def test_supported_profiles_are_normalized(profile):
    normalized = MODULE.normalize_profile(profile)
    assert normalized in MODULE.VALID_PROFILES


def test_invalid_profile_is_rejected():
    with pytest.raises(ValueError, match="invalid certification profile"):
        MODULE.normalize_profile("sandbox")


def test_markdown_contains_profile_decision_categories_and_change_control():
    report = MODULE.build_report([check("routing", "Reliability", "PASS")], "deployment-1", "pre-production")
    text = MODULE.render_markdown(report)
    assert "# MS-024A Profile-Aware Readiness Certification" in text
    assert "Pre-Production" in text
    assert "## Category results" in text
    assert "## Change control" in text
    assert "deployment-1" in text


def test_validator_applies_profile_specific_control_policy():
    text = (ROOT / "tools" / "validate" / "production_readiness_certification.sh").read_text()
    for token in (
        'CERTIFICATION_PROFILE:-pre-production',
        'profile" == "production"',
        "alarm_notifications",
        "cognito_waf",
        "readiness_enforcement",
        "terraform_readiness_gate",
        '--profile "$profile"',
        "describe-alarms",
        "us-east-1",
        "us-west-2",
    ):
        assert token in text


def test_activation_accepts_profile_and_publishes_profile_specific_record():
    text = (ROOT / "tools" / "resilience" / "activate_production_readiness_certification.sh").read_text()
    assert "--profile" in text
    assert "pre-production" in text
    assert 'if [[ "$status" -ne 0 ]]' in text
    assert "MS-024A_${profile_file}_READINESS_CERTIFICATION.md" in text


def test_documentation_records_profile_requirements_and_current_expected_result():
    text = (
        ROOT / "docs" / "architecture" / "platform-resilience" / "MS-024A_PRODUCTION_READINESS_PROFILES.md"
    ).read_text()
    assert "PRE_PRODUCTION_CERTIFIED" in text
    assert "productionReady" in text
    assert "Cognito WAF" in text
    assert "Alarm notification actions" in text
    assert "No AWS mutations are performed" in text
