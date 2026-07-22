from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dev_tfvars_example_requires_external_regional_certificates():
    text = (ROOT / "infra/global-api-routing.dev.tfvars.example").read_text()
    assert "enable_global_api_routing        = true" in text
    assert "manage_api_certificates" not in text
    assert "REPLACE_WITH_US_EAST_1_CERTIFICATE_ARN" in text
    assert "REPLACE_WITH_US_WEST_2_CERTIFICATE_ARN" in text
    assert 'route53_public_zone_id' in text


def test_global_edge_does_not_manage_acm_lifecycle():
    text = (ROOT / "infra/modules/global_edge/main.tf").read_text()
    assert 'resource "aws_acm_certificate"' not in text
    assert 'resource "aws_acm_certificate_validation"' not in text
    assert 'resource "aws_route53_record" "api_certificate_validation"' not in text
    assert "var.global_api.east_certificate_arn" in text
    assert "var.global_api.west_certificate_arn" in text


def test_global_edge_contract_requires_both_external_arns():
    variables = (ROOT / "infra/modules/global_edge/variables.tf").read_text()
    assert "manage_certificates" not in variables
    assert "trimspace(var.global_api.east_certificate_arn)" in variables
    assert "trimspace(var.global_api.west_certificate_arn)" in variables
    assert "validated external ACM certificate ARN" in variables


def test_certificate_helper_requests_both_regions_and_writes_tfvars():
    text = (ROOT / "tools/multi_site/prepare_external_acm_certificates.sh").read_text()
    assert "certificate_arn us-east-1" in text
    assert "certificate_arn us-west-2" in text
    assert "aws route53 change-resource-record-sets" in text
    assert "aws acm wait certificate-validated" in text
    assert "global-api-routing.generated.tfvars" in text
    assert "terraform apply" not in text


def test_global_edge_validation_script_is_read_only():
    text = (ROOT / "tools/multi_site/validate_global_api_edge.sh").read_text()
    assert " output -json global_api_routing" in text
    assert "terraform apply" not in text
    assert "terraform plan" not in text
    assert "aws route53 change-resource-record-sets" not in text


def test_global_edge_example_is_not_auto_loaded():
    infra = ROOT / "infra"
    assert (infra / "global-api-routing.dev.tfvars.example").is_file()
    assert not (infra / "global-api-routing.auto.tfvars").exists()
    assert not list(infra.glob("global-api-routing*.auto.tfvars"))
