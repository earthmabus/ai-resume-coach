from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence


PACKAGE_NAMES = (
    "api",
    "worker",
    "outbox_publisher",
    "registration_notification",
)

FORBIDDEN_PARTS = {
    ".aws",
    ".env",
    ".terraform",
    "__pycache__",
}
FORBIDDEN_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".tfstate",
    ".tfplan",
}


def write_aws_sdk_stubs(stub_root: Path) -> None:
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


def assert_no_forbidden_artifact_files(root: Path) -> None:
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in FORBIDDEN_PARTS for part in relative.parts):
            raise RuntimeError(f"Forbidden artifact path: {relative}")
        if path.is_file() and path.suffix in FORBIDDEN_SUFFIXES:
            raise RuntimeError(f"Forbidden artifact file: {relative}")


def import_handler(
    *,
    package_root: Path,
    layer_python_root: Path | None,
    stub_root: Path,
) -> None:
    python_path = [
        str(package_root),
        str(stub_root),
    ]
    if layer_python_root is not None:
        python_path.insert(1, str(layer_python_root))

    write_aws_sdk_stubs(stub_root)

    environment = {
        "PYTHONPATH": os.pathsep.join(python_path),
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

    result = subprocess.run(
        [sys.executable, "-S", "-c", "import handler"],
        cwd=package_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{package_root.name} handler import failed:\n"
            f"stdout={result.stdout}\n"
            f"stderr={result.stderr}"
        )


def validate_artifacts(repository_root: Path) -> None:
    package_root = repository_root / "build" / "lambda"
    layer_root = (
        repository_root / "build" / "lambda_layer" / "pdf_dependencies"
    )
    layer_python_root = layer_root / "python"

    for package_name in PACKAGE_NAMES:
        root = package_root / package_name
        if not (root / "handler.py").is_file():
            raise RuntimeError(f"Missing handler for package {package_name}")
        assert_no_forbidden_artifact_files(root)

    if not (layer_python_root / "pypdf").is_dir():
        raise RuntimeError("PDF dependency layer is missing python/pypdf")

    assert_no_forbidden_artifact_files(layer_root)

    stub_root = package_root / "_artifact_validation_stubs"
    if stub_root.exists():
        shutil.rmtree(stub_root)
    write_aws_sdk_stubs(stub_root)

    try:
        for package_name in PACKAGE_NAMES:
            import_handler(
                package_root=package_root / package_name,
                layer_python_root=(
                    layer_python_root if package_name == "api" else None
                ),
                stub_root=stub_root,
            )
    finally:
        if stub_root.exists():
            shutil.rmtree(stub_root)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate built Lambda deployment artifacts."
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    validate_artifacts(args.repository_root.resolve())
    print("Lambda deployment artifacts validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
