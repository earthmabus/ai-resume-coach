from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

for import_path in (
    ROOT,
    SRC,
):
    normalized_path = str(import_path)

    if normalized_path not in sys.path:
        sys.path.insert(
            0,
            normalized_path,
        )


TEST_ENVIRONMENT = {
    "PROJECT_NAME": "ai-resume-coach",
    "ENVIRONMENT": "test",
    "APP_VERSION": "test-version",
    "DEPLOYMENT_ID": "test-deployment",
    "AWS_REGION": "us-east-1",
    "AWS_DEFAULT_REGION": "us-east-1",
    "RESUME_ANALYSIS_TABLE": "test-table",
    "DOCUMENT_BUCKET": "test-bucket",
    "RESUME_ANALYSIS_QUEUE_URL": (
        "https://sqs.us-east-1.amazonaws.com/"
        "123456789012/test-queue"
    ),
    "WORKER_PROCESSING_LEASE_SECONDS": "300",
    "ANALYSIS_PROVIDER": "rule-based",
    "OPENAI_MODEL": "",
    "LOG_LEVEL": "INFO",
    "OUTBOX_BATCH_SIZE": "25",
    "OUTBOX_MAX_WORKERS": "4",
    "OUTBOX_MAX_DELIVERY_ATTEMPTS": "20",
    "OUTBOX_DELIVERED_RETENTION_SECONDS": "2592000",
}


# Establish required values before pytest imports application modules.
for variable_name, variable_value in TEST_ENVIRONMENT.items():
    os.environ.setdefault(
        variable_name,
        variable_value,
    )


@pytest.fixture(autouse=True)
def application_environment(
    monkeypatch,
):
    """
    Restore the baseline test environment before every test.

    Tests may temporarily modify values with monkeypatch.
    """
    for (
        variable_name,
        variable_value,
    ) in TEST_ENVIRONMENT.items():
        monkeypatch.setenv(
            variable_name,
            variable_value,
        )

    from core.config import reset_config_cache

    reset_config_cache()

    yield

    reset_config_cache()
