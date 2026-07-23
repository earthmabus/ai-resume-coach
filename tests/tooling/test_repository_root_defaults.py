from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tools.build.lambda_packages import parse_args as parse_lambda_package_args
from tools.validate.lambda_artifacts import parse_args as parse_artifact_args


ROOT = Path(__file__).resolve().parents[2]


def test_lambda_package_cli_defaults_to_repository_root():
    assert parse_lambda_package_args([]).repository_root.resolve() == ROOT


def test_lambda_artifact_cli_defaults_to_repository_root():
    assert parse_artifact_args([]).repository_root.resolve() == ROOT


def test_replay_outbox_bootstrap_uses_repository_src():
    script = ROOT / "tools" / "operations" / "replay_outbox.py"
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            (
                "import runpy; "
                f"ns = runpy.run_path({str(script)!r}, run_name='not_main'); "
                "print(ns['REPOSITORY_ROOT']); "
                "print(ns['SOURCE_DIRECTORY'])"
            ),
        ],
        cwd=ROOT / "tools",
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    assert lines == [str(ROOT), str(ROOT / "src")]
