from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_certificate_helper_enables_health_checks_in_generated_profile():
    text = (ROOT / "tools/prepare/external_acm_certificates.sh").read_text()
    generated = text.split('cat >"$OUTPUT_TFVARS"', 1)[1]
    assert "enable_global_api_routing        = true" in generated
    assert "enable_route53_api_health_checks = true" in generated
    assert 'chmod 600 "$OUTPUT_TFVARS"' in text


def test_activation_workflow_uses_saved_plan_and_explicit_apply_confirmation():
    text = (ROOT / "tools/resilience/activate_global_api_routing.sh").read_text()
    assert "CONFIRM_MUTATION=YES" in text
    assert "prepare_deployed_runtime_alignment" in text
    assert 'terraform -chdir="$INFRA_DIR" plan' in text
    assert 'terraform -chdir="$INFRA_DIR" apply' in text
    assert "ROUTING_PLAN_FILE" in text


def test_activation_workflow_does_not_depend_on_retired_runtime_profile():
    text = (ROOT / "tools/resilience/activate_global_api_routing.sh").read_text()
    assert "runtime-validation.tfvars" not in text
    assert "certification_profile.sh" not in text


def test_edge_validation_checks_latency_health_and_both_direct_sites():
    text = (ROOT / "tools/validate/global_api_edge.sh").read_text()
    assert '.health_checks_enabled == true' in text
    assert '.routing_policy == "LATENCY"' in text
    assert "for site in east west" in text
    assert "regional_api_endpoints" in text
    assert "terraform apply" not in text
    assert "TFVARS_FILE" not in text


def test_existing_terraform_contract_exposes_health_checked_latency_routing():
    module = (ROOT / "infra/modules/global_edge/main.tf").read_text()
    assert module.count("latency_routing_policy {") == 2
    assert 'resource_path     = "/health/ready"' in module
    assert "health_check_id = var.global_api.health_checks_enabled" in module
