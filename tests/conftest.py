import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def application_environment(monkeypatch):
    values = {
        "PROJECT_NAME": "ai-resume-coach",
        "ENVIRONMENT": "test",
        "APP_VERSION": "test-version",
        "DEPLOYMENT_ID": "test-deployment",
        "AWS_REGION": "us-east-1",
        "RESUME_ANALYSIS_TABLE": "test-table",
        "DOCUMENT_BUCKET": "test-bucket",
        "RESUME_ANALYSIS_QUEUE_URL": (
            "https://sqs.us-east-1.amazonaws.com/123456789012/test"
        ),
        "ANALYSIS_PROVIDER": "rule-based",
        "OPENAI_MODEL": "",
        "LOG_LEVEL": "INFO",
    }

    for name, value in values.items():
        monkeypatch.setenv(name, value)

    from core.config import reset_config_cache

    reset_config_cache()
    yield
    reset_config_cache()
