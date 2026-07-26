#!/usr/bin/env python3
"""Render the MS-023 production-observability evidence checks."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_checks(path: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if line.strip():
            checks.append(json.loads(line))
    return checks


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check for check in checks if check.get("status") == "FAIL"]
    warnings = [check for check in checks if check.get("status") == "WARN"]
    return {
        "schemaVersion": 1,
        "milestone": "MS-023",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "FAIL" if failed else "PASS",
        "summary": {
            "total": len(checks),
            "passed": sum(check.get("status") == "PASS" for check in checks),
            "warnings": len(warnings),
            "failed": len(failed),
        },
        "checks": checks,
        "boundaries": [
            "CloudWatch alarms may be deployed without notification actions; alarm state remains visible in CloudWatch.",
            "Synthetic canaries exercise only public health endpoints and do not authenticate or mutate application data.",
            "AWS X-Ray active tracing remains independently controlled and is not required by this slice.",
        ],
    }


def render(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "MS-023 Production Observability",
        "=================================",
        f"Status: {report['status']}",
        f"Checks: {summary['passed']}/{summary['total']} passed; {summary['warnings']} warning(s)",
        "",
    ]
    for check in report["checks"]:
        lines.append(f"[{check['status']}] {check['name']}: {check['detail']}")
    lines.extend(["", "Boundaries:"])
    lines.extend(f"- {item}" for item in report["boundaries"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checks", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    args = parser.parse_args()
    report = build_report(load_checks(args.checks))
    if args.json_path:
        args.json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(render(report))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
