from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_worker_enforces_persisted_and_message_ownership():
    text = (ROOT / "src/lambdas/worker/handler.py").read_text()
    assert "require_processing_ownership" in text
    assert 'persisted_owner_region=item.get("ownerRegion")' in text
    assert '"AND #ownerRegion = :expectedOwnerRegion "' in text


def test_processing_ownership_contract_fails_closed_without_automatic_transfer():
    text = (ROOT / "infra/outputs.tf").read_text()
    compact = " ".join(text.split())
    assert 'mode = "PERSISTED_OWNER_REGION"' in compact
    assert 'worker_enforcement = "FAIL_CLOSED"' in compact
    assert 'automatic_reassignment = false' in compact
    assert 'cross_region_queue_drain = false' in compact


def test_activation_preserves_prior_resilience_slices_and_saved_plan():
    text = (ROOT / "tools/resilience/activate_processing_ownership.sh").read_text()
    assert "global-api-routing.generated.tfvars" in text
    assert "enable_cognito_recovery=true" in text
    assert "enable_document_replication=true" in text
    assert "CONFIRM_MUTATION=YES" in text
    assert 'terraform -chdir="$INFRA_DIR" apply' in text


def test_validation_checks_contract_and_both_workers():
    text = (ROOT / "tools/validate/processing_ownership.sh").read_text()
    assert 'processing_ownership.value' in text
    assert text.count("get-function-configuration") == 2
    assert "automatic reassignment and cross-region queue draining remain out of scope" in text


def test_documentation_distinguishes_failover_from_owner_transfer():
    text = (
        ROOT
        / "docs/architecture/platform-resilience/MS-021_PROCESSING_OWNERSHIP.md"
    ).read_text()
    assert "Route 53 failover does not change `ownerRegion`" in text
    assert "controlled owner transfer" in text.lower()
