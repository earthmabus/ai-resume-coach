#!/usr/bin/env python3
"""Render the MS-022 disaster-recovery validation evidence as JSON or text."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    evidence: str | None = None


def load_checks(path: Path) -> list[Check]:
    checks: list[Check] = []
    for line_number, raw in enumerate(path.read_text().splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {line_number}: {exc}") from exc
        checks.append(
            Check(
                name=str(item["name"]),
                status=str(item["status"]),
                detail=str(item["detail"]),
                evidence=str(item["evidence"]) if item.get("evidence") else None,
            )
        )
    return checks


def build_report(checks: list[Check], mode: str) -> dict[str, object]:
    failed = [item for item in checks if item.status != "PASS"]
    return {
        "schemaVersion": 1,
        "milestone": "MS-022",
        "mode": mode,
        "status": "PASS" if not failed else "FAIL",
        "summary": {
            "total": len(checks),
            "passed": len(checks) - len(failed),
            "failed": len(failed),
        },
        "checks": [asdict(item) for item in checks],
        "limitations": [
            "No Route 53 records or health checks are disabled during this drill.",
            "No regional Lambda, queue, table, or API is intentionally made unavailable.",
            "Cognito recovery is contract-validated; users, passwords, and sessions are not failed over.",
            "Processing ownership transfer is contract-validated; ownerRegion is not changed automatically.",
        ],
    }


def render_text(report: dict[str, object]) -> str:
    summary = report["summary"]
    assert isinstance(summary, dict)
    lines = [
        "MS-022 Disaster-Recovery Validation",
        "====================================",
        f"Mode: {report['mode']}",
        f"Status: {report['status']}",
        f"Checks: {summary['passed']}/{summary['total']} passed",
        "",
    ]
    for item in report["checks"]:
        assert isinstance(item, dict)
        lines.append(f"[{item['status']}] {item['name']}: {item['detail']}")
    lines.extend(["", "Boundaries:"])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checks", type=Path, required=True)
    parser.add_argument("--mode", choices=("assess", "exercise"), required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        report = build_report(load_checks(args.checks), args.mode)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"Unable to build MS-022 report: {exc}", file=sys.stderr)
        return 2

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_text(report))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
