from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_replication_is_bidirectional_and_feature_gated():
    text = (ROOT / "infra/document_replication.tf").read_text()
    assert 'count    = var.enable_document_replication ? 1 : 0' in text
    assert 'resource "aws_s3_bucket_replication_configuration" "documents_east_to_west"' in text
    assert 'resource "aws_s3_bucket_replication_configuration" "documents_west_to_east"' in text
    assert 'Capability = "document-replication"' in text


def test_replication_permissions_are_narrow_and_version_aware():
    text = (ROOT / "infra/document_replication.tf").read_text()
    assert '"s3:GetObjectVersionForReplication"' in text
    assert '"s3:ReplicateObject"' in text
    assert '"s3:ReplicateDelete"' in text
    assert '"s3:*"' not in text


def test_contract_discloses_best_effort_and_no_existing_object_backfill():
    text = (ROOT / "infra/outputs.tf").read_text()
    assert 'mode              = "BIDIRECTIONAL_CRR"' in text
    assert 'existing_objects  = false' in text
    assert 'replication_time  = "BEST_EFFORT"' in text
    assert 'rtc_enabled       = false' in text


def test_activation_preserves_previous_resilience_slices_and_saved_plan():
    text = (ROOT / "tools/resilience/activate_document_replication.sh").read_text()
    assert "global-api-routing.generated.tfvars" in text
    assert "enable_cognito_recovery=true" in text
    assert "enable_document_replication=true" in text
    assert "CONFIRM_MUTATION=YES" in text
    assert 'terraform -chdir="$INFRA_DIR" apply' in text


def test_validation_checks_both_buckets_and_replication_directions():
    text = (ROOT / "tools/validate/document_replication.sh").read_text()
    assert text.count("get-bucket-versioning") == 2
    assert text.count("get-bucket-replication") == 2
    assert "ordinary CRR applies to new object versions" in text
