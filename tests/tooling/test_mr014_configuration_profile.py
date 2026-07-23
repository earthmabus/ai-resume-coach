import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools/prepare/configuration_profile.py"
spec = importlib.util.spec_from_file_location("mr014_profile", TOOL)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def complete_text():
    return """
enable_global_api_routing = true
enable_route53_api_health_checks = true
enable_outbox_publisher_schedule = true
enable_synthetic_placement_override = true
api_domain_name = "api.example.com"
route53_public_zone_id = "Z1234567890ABC"
east_api_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/11111111-1111-1111-1111-111111111111"
west_api_certificate_arn = "arn:aws:acm:us-west-2:123456789012:certificate/22222222-2222-2222-2222-222222222222"
site_routing_enabled = { east = true, west = true }
"""


def test_complete_profile_is_valid():
    result = module.validate_profile(complete_text())
    assert result["valid"] is True
    assert result["errors"] == []


def test_incomplete_routing_only_profile_is_rejected():
    result = module.validate_profile("enable_global_api_routing = true\nenable_route53_api_health_checks = true\n")
    assert result["valid"] is False
    assert any("enable_outbox_publisher_schedule" in error for error in result["errors"])
    assert any("enable_synthetic_placement_override" in error for error in result["errors"])



def test_profile_missing_required_routing_identity_is_rejected():
    text = complete_text().replace('api_domain_name = "api.example.com"\n', "")
    result = module.validate_profile(text)
    assert result["valid"] is False
    assert any("api_domain_name" in error for error in result["errors"])


def test_profile_rejects_empty_required_routing_identity():
    text = complete_text().replace(
        'route53_public_zone_id = "Z1234567890ABC"',
        'route53_public_zone_id = ""',
    )
    result = module.validate_profile(text)
    assert result["valid"] is False
    assert any("route53_public_zone_id" in error for error in result["errors"])


def test_profile_rejects_certificate_arn_in_wrong_region():
    text = complete_text().replace(
        "arn:aws:acm:us-west-2:",
        "arn:aws:acm:us-east-1:",
    )
    result = module.validate_profile(text)
    assert result["valid"] is False
    assert any("west_api_certificate_arn" in error for error in result["errors"])


def test_placeholders_are_rejected():
    result = module.validate_profile(complete_text() + 'note = "<deployment>"\n')
    assert result["valid"] is False
    assert any("placeholder" in error for error in result["errors"])


def test_composition_rejects_duplicate_assignments(tmp_path):
    one = tmp_path / "one.tfvars"
    two = tmp_path / "two.tfvars"
    one.write_text("enable_global_api_routing = true\n")
    two.write_text("enable_global_api_routing = true\n")
    try:
        module.compose([one, two])
    except ValueError as exc:
        assert "duplicate variable" in str(exc)
    else:
        raise AssertionError("duplicate assignment was accepted")


def test_repository_runtime_and_routing_profiles_compose(tmp_path):
    output = tmp_path / "certification.tfvars"
    subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "compose",
            "--input",
            str(ROOT / "infra/runtime-validation.tfvars.example"),
            "--input",
            str(ROOT / "infra/global-api-routing.generated.tfvars.example"),
            "--output",
            str(output),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    assert module.validate_profile(output.read_text())["valid"] is True


def test_chaos_harness_validates_profile_before_mutation():
    chaos = (ROOT / "tools/validate/chaos.sh").read_text()
    runtime = (ROOT / "tools/validate/failover_runtime.sh").read_text()
    assert "certification_profile.sh\" validate" in chaos
    assert "configuration_profile.py\" validate" in runtime
