from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "operations" / "delete_orphaned_job_match_children.sh"


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(0o755)


def _run_script(tmp_path: Path, *, args: list[str], terraform_body: str, aws_body: str):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_executable(fake_bin / "terraform", terraform_body)
    _write_executable(fake_bin / "aws", aws_body)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env.pop("TABLE_NAME", None)
    return subprocess.run(
        [str(SCRIPT), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cleanup_tool_reads_structured_terraform_table_output(tmp_path: Path):
    terraform_body = """#!/usr/bin/env bash
if [[ "$*" == *"output -json resume_analysis_data"* ]]; then
  printf '%s\n' '{"table_name":"ai-resume-coach-dev-resume-analysis"}'
  exit 0
fi
exit 1
"""
    aws_body = """#!/usr/bin/env bash
if [[ "$*" == *"dynamodb get-item"* ]]; then
  printf '%s\n' '{}'
elif [[ "$*" == *"dynamodb query"* ]]; then
  printf '%s\n' '{"Items":[]}'
else
  exit 99
fi
"""
    result = _run_script(
        tmp_path,
        args=["--user-id", "user-1", "--match-id", "match-1"],
        terraform_body=terraform_body,
        aws_body=aws_body,
    )

    assert result.returncode == 0, result.stderr
    assert "Table: ai-resume-coach-dev-resume-analysis" in result.stdout
    assert "Orphaned child records found: 0" in result.stdout


def test_explicit_table_and_profile_bypass_terraform_discovery(tmp_path: Path):
    aws_log = tmp_path / "aws.log"
    terraform_body = """#!/usr/bin/env bash
exit 88
"""
    aws_body = f"""#!/usr/bin/env bash
printf '%s\n' "$*" >> {str(aws_log)!r}
if [[ "$*" == *"dynamodb get-item"* ]]; then
  printf '%s\n' '{{}}'
elif [[ "$*" == *"dynamodb query"* ]]; then
  printf '%s\n' '{{"Items":[]}}'
else
  exit 99
fi
"""
    result = _run_script(
        tmp_path,
        args=[
            "--table-name",
            "explicit-table",
            "--region",
            "us-west-2",
            "--profile",
            "dev-admin",
            "--user-id",
            "user-1",
            "--match-id",
            "match-1",
        ],
        terraform_body=terraform_body,
        aws_body=aws_body,
    )

    assert result.returncode == 0, result.stderr
    assert "Table: explicit-table" in result.stdout
    assert "Region: us-west-2" in result.stdout
    assert "Profile: dev-admin" in result.stdout
    calls = aws_log.read_text()
    assert "--region us-west-2 --profile dev-admin" in calls
    assert "--table-name explicit-table" in calls


def test_aws_discovery_requires_a_unique_matching_table(tmp_path: Path):
    terraform_body = """#!/usr/bin/env bash
exit 1
"""
    aws_body = """#!/usr/bin/env bash
if [[ "$*" == *"dynamodb list-tables"* ]]; then
  printf '%s\n' '{"TableNames":["ai-resume-coach-dev-resume-analysis"]}'
elif [[ "$*" == *"dynamodb get-item"* ]]; then
  printf '%s\n' '{}'
elif [[ "$*" == *"dynamodb query"* ]]; then
  printf '%s\n' '{"Items":[]}'
else
  exit 99
fi
"""
    result = _run_script(
        tmp_path,
        args=["--user-id", "user-1", "--match-id", "match-1"],
        terraform_body=terraform_body,
        aws_body=aws_body,
    )

    assert result.returncode == 0, result.stderr
    assert "Table: ai-resume-coach-dev-resume-analysis" in result.stdout


def test_help_documents_resolution_and_profile_support():
    result = subprocess.run(
        [str(SCRIPT), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--profile PROFILE" in result.stdout
    assert "Terraform resume_analysis_data.table_name output" in result.stdout
    assert "A unique AWS table containing" in result.stdout
