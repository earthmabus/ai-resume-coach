import pytest

from core.config import ConfigurationError, get_config, reset_config_cache


def test_get_config_reads_required_values():
    config = get_config()

    assert config.project_name == "ai-resume-coach"
    assert config.environment == "test"
    assert config.app_version == "test-version"
    assert config.deployment_id == "test-deployment"
    assert config.aws_region == "us-east-1"
    assert config.table_name == "test-table"
    assert config.document_bucket == "test-bucket"
    assert config.processing_queue_url.endswith("/test")


def test_missing_aws_region_raises(monkeypatch):
    monkeypatch.delenv("AWS_REGION", raising=False)
    reset_config_cache()

    with pytest.raises(ConfigurationError):
        get_config()


def test_missing_table_name_raises(monkeypatch):
    monkeypatch.delenv("RESUME_ANALYSIS_TABLE", raising=False)
    reset_config_cache()

    with pytest.raises(ConfigurationError):
        get_config()


def test_defaults_are_applied(monkeypatch):
    monkeypatch.delenv("PROJECT_NAME", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.delenv("DEPLOYMENT_ID", raising=False)
    monkeypatch.delenv("ANALYSIS_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    reset_config_cache()
    config = get_config()

    assert config.project_name == "ai-resume-coach"
    assert config.environment == "dev"
    assert config.app_version == "0.1.0"
    assert config.deployment_id == "local"
    assert config.analysis_provider == "rule-based"
    assert config.openai_model == ""
    assert config.log_level == "INFO"


def test_config_cache_can_be_reset(monkeypatch):
    first = get_config()
    assert first.environment == "test"

    monkeypatch.setenv("ENVIRONMENT", "changed")
    reset_config_cache()

    second = get_config()
    assert second.environment == "changed"
