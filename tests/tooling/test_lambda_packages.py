from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools.build.pdf_dependency_layer import build_pdf_dependency_layer
from tools.build.lambda_packages import build_all_packages


ROOT = Path(__file__).resolve().parents[2]
BUILD_ROOT = ROOT / "build" / "lambda"
LAYER_ROOT = ROOT / "build" / "lambda_layer" / "pdf_dependencies"


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
    assert any(path.startswith("core/") for path in worker_files)
    assert "core/retry_policy.py" in worker_files
    assert any(path.startswith("providers/") for path in worker_files)
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


def write_aws_sdk_stubs(stub_root: Path) -> Path:
    (stub_root / "boto3" / "dynamodb").mkdir(parents=True, exist_ok=True)
    (stub_root / "botocore").mkdir(parents=True, exist_ok=True)

    (stub_root / "boto3" / "__init__.py").write_text(
        "class _Resource:\n"
        "    def Table(self, *args, **kwargs):\n"
        "        return object()\n"
        "\n"
        "def client(*args, **kwargs):\n"
        "    return object()\n"
        "\n"
        "def resource(*args, **kwargs):\n"
        "    return _Resource()\n",
        encoding="utf-8",
    )
    (stub_root / "boto3" / "dynamodb" / "__init__.py").write_text(
        "",
        encoding="utf-8",
    )
    (stub_root / "boto3" / "dynamodb" / "conditions.py").write_text(
        "class Key:\n"
        "    def __init__(self, *args, **kwargs):\n"
        "        pass\n",
        encoding="utf-8",
    )
    (stub_root / "boto3" / "dynamodb" / "types.py").write_text(
        "class TypeSerializer:\n"
        "    pass\n",
        encoding="utf-8",
    )
    (stub_root / "botocore" / "__init__.py").write_text(
        "",
        encoding="utf-8",
    )
    (stub_root / "botocore" / "config.py").write_text(
        "class Config:\n"
        "    def __init__(self, *args, **kwargs):\n"
        "        pass\n",
        encoding="utf-8",
    )
    (stub_root / "botocore" / "exceptions.py").write_text(
        "class BotoCoreError(Exception):\n"
        "    pass\n"
        "\n"
        "class ClientError(Exception):\n"
        "    def __init__(self, error_response=None, operation_name=''):\n"
        "        self.response = error_response or {}\n"
        "        super().__init__(str(self.response))\n",
        encoding="utf-8",
    )

    return stub_root


def import_package_handler(package_name: str, *, layer_root=None, extra_env=None):
    package_root = BUILD_ROOT / package_name
    stub_root = package_root.parent / "_aws_sdk_stubs"
    if stub_root.exists():
        import shutil

        shutil.rmtree(stub_root)
    write_aws_sdk_stubs(stub_root)

    python_path_entries = [
        str(package_root),
        str(stub_root),
    ]
    if layer_root is not None:
        python_path_entries.insert(1, str(layer_root / "python"))

    write_aws_sdk_stubs(stub_root)

    environment = {
        "PYTHONPATH": os.pathsep.join(python_path_entries),
        "PYTHONDONTWRITEBYTECODE": "1",
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
        [sys.executable, "-S", "-c", "import handler"],
        cwd=package_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_each_built_handler_imports_in_isolation():
    build_all_packages(repository_root=ROOT)
    fake_layer_root = BUILD_ROOT.parent / "test_pdf_layer"
    (fake_layer_root / "python" / "pypdf").mkdir(parents=True, exist_ok=True)
    (fake_layer_root / "python" / "pypdf" / "__init__.py").write_text(
        "class PdfReader:\n"
        "    pass\n",
        encoding="utf-8",
    )

    package_layers = {
        "api": fake_layer_root,
        "worker": None,
        "outbox_publisher": None,
        "registration_notification": None,
    }

    for package_name, layer_root in package_layers.items():
        result = import_package_handler(
            package_name,
            layer_root=layer_root,
        )
        assert result.returncode == 0, (
            f"{package_name} import failed:\n"
            f"stdout={result.stdout}\n"
            f"stderr={result.stderr}"
        )


def test_pdf_dependency_layer_builder_targets_lambda_runtime(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, check):
        calls.append(command)
        target = Path(command[command.index("--target") + 1])
        (target / "pypdf").mkdir(parents=True)

    monkeypatch.setattr("subprocess.run", fake_run)

    layer_root = build_pdf_dependency_layer(
        repository_root=ROOT,
        output_root=tmp_path / "layer",
    )

    assert (layer_root / "python" / "pypdf").is_dir()
    assert calls
    command = calls[0]
    assert "--platform" in command
    assert command[command.index("--platform") + 1] == "manylinux2014_aarch64"
    assert "--python-version" in command
    assert command[command.index("--python-version") + 1] == "3.13"
    assert "--abi" in command
    assert command[command.index("--abi") + 1] == "cp313"
    assert "--only-binary=:all:" in command


def test_pdf_dependency_layer_artifact_contains_runtime_packages():
    if not LAYER_ROOT.exists():
        pytest.skip("PDF dependency layer has not been built")

    assert (LAYER_ROOT / "python" / "pypdf").is_dir()
    assert (LAYER_ROOT / "python" / "openai").is_dir()
    assert not any("__pycache__" in path.parts for path in LAYER_ROOT.rglob("*"))
    assert not any(path.suffix == ".pyc" for path in LAYER_ROOT.rglob("*"))


def test_api_handler_import_fails_without_pdf_dependency_layer():
    build_all_packages(repository_root=ROOT)

    result = import_package_handler("api")

    assert result.returncode != 0
    assert "No module named 'pypdf'" in result.stderr


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
