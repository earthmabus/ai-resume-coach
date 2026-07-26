from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_recovery_pool_is_west_only_and_feature_gated():
    text = (ROOT / "infra/identity_recovery.tf").read_text()
    assert 'provider = aws.us_west_2' in text
    assert 'count    = var.enable_cognito_recovery ? 1 : 0' in text
    assert 'Capability = "identity-recovery"' in text


def test_recovery_contract_does_not_claim_seamless_failover():
    text = (ROOT / "infra/outputs.tf").read_text()
    assert 'mode    = "WARM_STANDBY_RESET_REQUIRED"' in text
    assert "password_continuity = false" in text
    assert "session_continuity  = false" in text
    assert "automated_failover  = false" in text


def test_activation_preserves_ms018_routing_and_uses_saved_plan():
    text = (ROOT / "tools/resilience/activate_identity_recovery.sh").read_text()
    assert "global-api-routing.generated.tfvars" in text
    assert '-var-file="$BASELINE_TFVARS_FILE"' in text
    assert "enable_cognito_recovery=true" in text
    assert "CONFIRM_MUTATION=YES" in text
    assert 'terraform -chdir="$INFRA_DIR" apply' in text


def test_validation_checks_both_resources_and_limitations():
    text = (ROOT / "tools/validate/identity_recovery.sh").read_text()
    assert "describe-user-pool" in text
    assert "describe-user-pool-client" in text
    assert ".password_continuity == false" in text
    assert ".automated_failover == false" in text


def test_documentation_states_cognito_replication_limit():
    text = (ROOT / "docs/architecture/platform-resilience/MS-019_IDENTITY_RECOVERY.md").read_text()
    assert "do not provide native cross-Region user-pool" in text
    assert "Password verifiers" in text
    assert "80/100" in text
