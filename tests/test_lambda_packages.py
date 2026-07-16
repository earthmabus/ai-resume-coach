from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from tools.build_lambda_packages import build_all_packages


ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = ROOT / "build" / "lambda"


def built_files(package_name: str) -> set[str]:
    package_root = BUILD_ROOT / package_name
    return {
        path.relative_to(package_root).as_posix()
        for path in package_root.rglob("*")
        if path.is_file()
    }


def test_builds_expected_isolated_packages():
    build_all_packages(repository_root=ROOT)

    api_files = built_files("api")
    worker_files = built_files("worker")
    publisher_files = built_files("outbox_publisher")
    registration_files = built_files(
        "registration_notification"
    )

    assert "handler.py" in api_files
    assert any(path.startswith("core/") for path in api_files)
    assert any(path.startswith("features/") for path in api_files)
    assert any(path.startswith("providers/") for path in api_files)

    assert "handler.py" in worker_files
    assert any(path.startswith("providers/") for path in worker_files)
    assert not any(path.startswith("core/") for path in worker_files)
    assert not any(path.startswith("features/") for path in worker_files)

    assert "handler.py" in publisher_files
    assert any(path.startswith("core/") for path in publisher_files)
    assert not any(path.startswith("features/") for path in publisher_files)
    assert not any(path.startswith("providers/") for path in publisher_files)

    assert registration_files == {"handler.py"}


def test_packages_exclude_cache_and_test_files():
    build_all_packages(repository_root=ROOT)

    for package_root in BUILD_ROOT.iterdir():
        files = built_files(package_root.name)
        assert not any("__pycache__" in path for path in files)
        assert not any(path.endswith(".pyc") for path in files)
        assert not any(path.startswith("tests/") for path in files)


def import_package_handler(package_name: str, extra_env=None):
    package_root = BUILD_ROOT / package_name
    environment = {
        **os.environ,
        "PYTHONPATH": str(package_root),
        "AWS_EC2_METADATA_DISABLED": "true",
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_REGION": "us-east-1",
        "AWS_DEFAULT_REGION": "us-east-1",
        "PROJECT_NAME": "ai-resume-coach",
        "ENVIRONMENT": "test",
        "APP_VERSION": "test",
        "DEPLOYMENT_ID": "test",
        "LOG_LEVEL": "INFO",
        "RESUME_ANALYSIS_TABLE": "test-table",
        "DOCUMENT_BUCKET": "test-bucket",
        "RESUME_ANALYSIS_QUEUE_URL": (
            "https://sqs.us-east-1.amazonaws.com/123456789012/test"
        ),
        "ANALYSIS_PROVIDER": "rule-based",
        "OPENAI_MODEL": "",
        "OPENAI_API_KEY": "",
        "REGISTRATION_NOTIFICATION_TOPIC_ARN": (
            "arn:aws:sns:us-east-1:123456789012:test"
        ),
    }
    if extra_env:
        environment.update(extra_env)

    return subprocess.run(
        [sys.executable, "-c", "import handler"],
        cwd=package_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_each_built_handler_imports_in_isolation():
    build_all_packages(repository_root=ROOT)

    for package_name in (
        "api",
        "worker",
        "outbox_publisher",
        "registration_notification",
    ):
        result = import_package_handler(package_name)
        assert result.returncode == 0, (
            f"{package_name} import failed:\n"
            f"stdout={result.stdout}\n"
            f"stderr={result.stderr}"
        )


def test_build_is_deterministic_for_unchanged_sources():
    first = build_all_packages(repository_root=ROOT)
    first_contents = {
        package: {
            path.as_posix(): (
                BUILD_ROOT / package / path
            ).read_bytes()
            for path in files
        }
        for package, files in first.items()
    }

    second = build_all_packages(repository_root=ROOT)
    second_contents = {
        package: {
            path.as_posix(): (
                BUILD_ROOT / package / path
            ).read_bytes()
            for path in files
        }
        for package, files in second.items()
    }

    assert first_contents == second_contents
