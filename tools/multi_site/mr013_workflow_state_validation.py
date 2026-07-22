#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from core.workflow_state import (
    TERMINAL_STATUSES,
    allowed_targets,
    known_statuses,
)

SCHEMA_VERSION = 1


def build_report() -> dict:
    statuses = known_statuses()
    transitions = {
        status: sorted(allowed_targets(status))
        for status in statuses
    }
    errors: list[str] = []

    unknown_targets = sorted(
        {
            target
            for targets in transitions.values()
            for target in targets
            if target not in statuses
        }
    )
    if unknown_targets:
        errors.append(f"unknown transition targets: {unknown_targets}")

    terminal_with_edges = {
        status: transitions[status]
        for status in sorted(TERMINAL_STATUSES)
        if transitions.get(status)
    }
    if terminal_with_edges:
        errors.append(f"terminal states have outbound transitions: {terminal_with_edges}")

    missing_terminal_states = sorted(set(TERMINAL_STATUSES) - set(statuses))
    if missing_terminal_states:
        errors.append(f"terminal states are not known: {missing_terminal_states}")

    edge_count = sum(len(targets) for targets in transitions.values())
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "result": "PASS" if not errors else "FAIL",
        "summary": {
            "statusCount": len(statuses),
            "transitionCount": edge_count,
            "terminalCount": len(TERMINAL_STATUSES),
            "errorCount": len(errors),
        },
        "terminalStatuses": sorted(TERMINAL_STATUSES),
        "transitions": transitions,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and export the MR-013 workflow-state contract."
    )
    parser.add_argument("--output", type=Path, help="Optional JSON report path.")
    args = parser.parse_args()

    report = build_report()
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")

    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
