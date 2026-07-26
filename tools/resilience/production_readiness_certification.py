#!/usr/bin/env python3
"""Build the MS-024A profile-aware readiness certification report."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_STATUSES = {"PASS", "WARN", "FAIL"}
VALID_PROFILES = {"development", "integration", "pre-production", "production"}
PROFILE_LABELS = {
    "development": "Development",
    "integration": "Integration",
    "pre-production": "Pre-Production",
    "production": "Production",
}
PROFILE_STATUS_PREFIXES = {
    "development": "DEVELOPMENT",
    "integration": "INTEGRATION",
    "pre-production": "PRE_PRODUCTION",
    "production": "PRODUCTION",
}


@dataclass(frozen=True)
class Check:
    name: str
    category: str
    status: str
    detail: str
    evidence: str | None = None


def normalize_profile(value: str) -> str:
    profile = value.strip().lower().replace("_", "-")
    if profile not in VALID_PROFILES:
        allowed = ", ".join(sorted(VALID_PROFILES))
        raise ValueError(f"invalid certification profile {value!r}; expected one of: {allowed}")
    return profile


def load_checks(path: Path) -> list[Check]:
    checks: list[Check] = []
    for line_number, raw in enumerate(path.read_text().splitlines(), start=1):
        if not raw.strip():
            continue
        item = json.loads(raw)
        status = str(item["status"])
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid status at line {line_number}: {status}")
        checks.append(
            Check(
                name=str(item["name"]),
                category=str(item["category"]),
                status=status,
                detail=str(item["detail"]),
                evidence=str(item["evidence"]) if item.get("evidence") else None,
            )
        )
    if not checks:
        raise ValueError("no certification checks were supplied")
    return checks


def build_report(checks: list[Check], deployment_id: str, profile: str) -> dict[str, Any]:
    profile = normalize_profile(profile)
    failures = [check for check in checks if check.status == "FAIL"]
    warnings = [check for check in checks if check.status == "WARN"]
    categories: dict[str, dict[str, int | str]] = {}
    for category in sorted({check.category for check in checks}):
        category_checks = [check for check in checks if check.category == category]
        category_failures = sum(check.status == "FAIL" for check in category_checks)
        category_warnings = sum(check.status == "WARN" for check in category_checks)
        categories[category] = {
            "status": "FAIL" if category_failures else ("WARN" if category_warnings else "PASS"),
            "total": len(category_checks),
            "passed": sum(check.status == "PASS" for check in category_checks),
            "warnings": category_warnings,
            "failed": category_failures,
        }

    if failures:
        status = "NOT_CERTIFIED"
    else:
        status = f"{PROFILE_STATUS_PREFIXES[profile]}_CERTIFIED"
        if profile == "production" and warnings:
            status = "PRODUCTION_CERTIFIED_WITH_EXCEPTIONS"

    profile_ready = not failures
    return {
        "schemaVersion": 2,
        "milestone": "MS-024A",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "deploymentId": deployment_id,
        "profile": profile,
        "profileLabel": PROFILE_LABELS[profile],
        "status": status,
        "profileReady": profile_ready,
        "productionReady": profile == "production" and profile_ready,
        "hasExceptions": bool(warnings),
        "summary": {
            "total": len(checks),
            "passed": sum(check.status == "PASS" for check in checks),
            "warnings": len(warnings),
            "failed": len(failures),
        },
        "categories": categories,
        "checks": [asdict(check) for check in checks],
        "blockers": [check.detail for check in failures],
        "exceptions": [check.detail for check in warnings],
        "certifiedBoundaries": [
            "Certification applies only to the selected deployment profile.",
            "Bounded loss or isolation of either active application region.",
            "Warm-standby identity recovery requires password reset and does not preserve sessions.",
            "Processing ownership remains fail-closed; automatic reassignment and cross-region queue draining are not claimed.",
            "Synthetic monitoring covers public health endpoints only.",
        ],
    }


def render_text(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "MS-024A Production Readiness Profiles",
        "=======================================",
        f"Profile: {report['profileLabel']} ({report['profile']})",
        f"Status: {report['status']}",
        f"Profile ready: {'YES' if report['profileReady'] else 'NO'}",
        f"Production ready: {'YES' if report['productionReady'] else 'NO'}",
        f"Deployment ID: {report['deploymentId']}",
        f"Checks: {summary['passed']}/{summary['total']} passed; {summary['warnings']} warning(s); {summary['failed']} failure(s)",
        "",
    ]
    for category, result in report["categories"].items():
        lines.append(f"[{result['status']}] {category}: {result['passed']}/{result['total']} passed")
    if report["blockers"]:
        lines.extend(["", "Certification blockers:"])
        lines.extend(f"- {item}" for item in report["blockers"])
    if report["exceptions"]:
        lines.extend(["", "Accepted profile exceptions / warnings:"])
        lines.extend(f"- {item}" for item in report["exceptions"])
    return "\n".join(lines)


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# MS-024A Profile-Aware Readiness Certification",
        "",
        "## Decision",
        "",
        f"**{report['status'].replace('_', ' ')} — generated {report['generatedAt']}.**",
        "",
        f"Profile: **{report['profileLabel']}** (`{report['profile']}`)  ",
        f"Profile ready: **{'YES' if report['profileReady'] else 'NO'}**  ",
        f"Production ready: **{'YES' if report['productionReady'] else 'NO'}**  ",
        f"Deployment ID: `{report['deploymentId']}`",
        "",
        "## Summary",
        "",
        f"- Checks: {summary['passed']} passed, {summary['warnings']} warnings, {summary['failed']} failed.",
        "- Warnings are accepted profile exceptions; failed required controls block certification.",
        "- This record is generated from Terraform outputs and live AWS control-plane validation.",
        "",
        "## Category results",
        "",
        "| Category | Status | Passed | Warnings | Failed |",
        "|---|---:|---:|---:|---:|",
    ]
    for category, result in report["categories"].items():
        lines.append(
            f"| {category} | {result['status']} | {result['passed']}/{result['total']} | {result['warnings']} | {result['failed']} |"
        )
    lines.extend(["", "## Detailed checks", ""])
    for check in report["checks"]:
        evidence = f" Evidence: `{check['evidence']}`." if check.get("evidence") else ""
        lines.append(f"- **{check['status']} — {check['name']} ({check['category']}):** {check['detail']}{evidence}")
    if report["blockers"]:
        lines.extend(["", "## Certification blockers", ""])
        lines.extend(f"- {item}" for item in report["blockers"])
    if report["exceptions"]:
        lines.extend(["", "## Accepted profile exceptions and warnings", ""])
        lines.extend(f"- {item}" for item in report["exceptions"])
    lines.extend(["", "## Certified boundaries", ""])
    lines.extend(f"- {item}" for item in report["certifiedBoundaries"])
    lines.extend(
        [
            "",
            "## Change control",
            "",
            "Re-run MS-024A after changing the deployment profile or making material changes to routing, identity, persistence, processing ownership, observability, security controls, or readiness enforcement.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checks", type=Path, required=True)
    parser.add_argument("--deployment-id", required=True)
    parser.add_argument("--profile", default="pre-production")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--certification", type=Path, required=True)
    args = parser.parse_args()
    try:
        profile = normalize_profile(args.profile)
        report = build_report(load_checks(args.checks), args.deployment_id, profile)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Unable to build MS-024A certification: {exc}")
        return 2
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.certification.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    args.certification.write_text(render_markdown(report))
    print(render_text(report))
    return 0 if report["profileReady"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
