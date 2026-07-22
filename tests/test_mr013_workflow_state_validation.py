from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from core.workflow_state import (
    STATUS_COMPLETED,
    STATUS_FAILED_PERMANENT,
    STATUS_FAILED_RETRY_EXHAUSTED,
    STATUS_QUEUED,
    STATUS_QUEUED_PENDING_DISPATCH,
    allowed_targets,
    known_statuses,
)
from tools.multi_site.mr013_workflow_state_validation import build_report


ROOT = Path(__file__).resolve().parents[1]


def test_public_state_contract_matches_dispatch_transition():
    assert STATUS_QUEUED_PENDING_DISPATCH in known_statuses()
    assert allowed_targets(STATUS_QUEUED_PENDING_DISPATCH) == frozenset(
        {STATUS_QUEUED, "WORKER_PROCESSING"}
    )


def test_contract_report_is_closed_and_terminal_states_have_no_edges():
    report = build_report()

    assert report["result"] == "PASS"
    assert report["summary"]["errorCount"] == 0
    for terminal in (
        STATUS_COMPLETED,
        STATUS_FAILED_PERMANENT,
        STATUS_FAILED_RETRY_EXHAUSTED,
    ):
        assert report["transitions"][terminal] == []


def test_cli_writes_machine_readable_evidence(tmp_path):
    output = tmp_path / "report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/multi_site/mr013_workflow_state_validation.py"),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["result"] == "PASS"
    assert report["summary"]["statusCount"] == len(known_statuses())
