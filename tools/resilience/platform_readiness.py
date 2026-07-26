#!/usr/bin/env python3
"""Produce a lightweight multi-site resilience readiness assessment."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Capability:
    name: str
    status: str
    weight: int
    detail: str
    blocker: str | None = None


def terraform_outputs(infra_dir: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["terraform", f"-chdir={infra_dir}", "output", "-json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout or "{}")


def output_value(outputs: dict[str, Any], key: str) -> Any:
    entry = outputs.get(key)
    if not isinstance(entry, dict) or "value" not in entry:
        raise KeyError(f"Terraform output is missing: {key}")
    return entry["value"]


def capability(name: str, ready: bool, weight: int, ready_detail: str, blocked_detail: str, blocker: str) -> Capability:
    return Capability(
        name=name,
        status="READY" if ready else "BLOCKED",
        weight=weight,
        detail=ready_detail if ready else blocked_detail,
        blocker=None if ready else blocker,
    )


def assess(outputs: dict[str, Any]) -> dict[str, Any]:
    sites = output_value(outputs, "regional_sites")
    data = output_value(outputs, "resume_analysis_data")
    routing = output_value(outputs, "global_api_routing")
    foundations = output_value(outputs, "regional_foundations")

    active_regions = {
        sites.get("east", {}).get("region"),
        sites.get("west", {}).get("region"),
    }
    active_regions.discard(None)
    expected_regions = {"us-east-1", "us-west-2"}

    document_buckets = {
        foundations.get("east", {}).get("document_bucket", {}).get("name"),
        foundations.get("west", {}).get("document_bucket", {}).get("name"),
    }
    document_buckets.discard(None)

    capabilities = [
        capability(
            "regional_application_sites",
            active_regions == expected_regions,
            20,
            "Both active application Regions are represented.",
            f"Expected {sorted(expected_regions)}; found {sorted(active_regions)}.",
            "Complete symmetric regional application deployment.",
        ),
        capability(
            "dynamodb_mrsc",
            set(data.get("replica_regions", [])) == expected_regions
            and data.get("witness_region") == "us-east-2"
            and data.get("consistency_mode") == "STRONG",
            25,
            "MRSC uses east/west replicas with the us-east-2 witness.",
            "The DynamoDB output does not match the approved MRSC topology.",
            "Reconcile the DynamoDB MRSC replica and witness configuration.",
        ),
        capability(
            "global_api_latency_routing",
            routing.get("enabled") is True,
            20,
            "Route 53 latency routing is enabled.",
            "Route 53 latency routing is disabled.",
            "Enable global API routing with the approved custom-domain configuration.",
        ),
        capability(
            "route53_health_checks",
            routing.get("health_checks_enabled") is True,
            15,
            "Route 53 health checks are enabled.",
            "Route 53 health checks are disabled.",
            "Enable health checks against /health/ready for both regional APIs.",
        ),
        capability(
            "identity_recovery",
            bool(outputs.get("cognito_recovery"))
            and bool(output_value(outputs, "cognito_recovery").get("enabled"))
            and output_value(outputs, "cognito_recovery").get("mode") == "WARM_STANDBY_RESET_REQUIRED"
            and output_value(outputs, "cognito_recovery").get("password_continuity") is False
            and output_value(outputs, "cognito_recovery").get("session_continuity") is False
            and output_value(outputs, "cognito_recovery").get("automated_failover") is False,
            10,
            "Warm-standby identity recovery is enabled with password reset and no session continuity.",
            "No truthful enabled warm-standby identity-recovery contract is exposed.",
            "Enable and validate the controlled Cognito recovery pool and reset-required runbook.",
        ),
        capability(
            "document_continuity",
            bool(outputs.get("document_replication"))
            and bool(output_value(outputs, "document_replication").get("enabled")),
            10,
            "Cross-Region document replication is represented and enabled.",
            f"Regional document buckets exist ({len(document_buckets)}), but no replication contract is exposed.",
            "Implement and validate cross-Region document replication and survivor reads.",
        ),
    ]

    score = sum(item.weight for item in capabilities if item.status == "READY")
    blockers = [item.blocker for item in capabilities if item.blocker]
    return {
        "schemaVersion": 1,
        "milestone": "MS-022",
        "score": score,
        "maximumScore": sum(item.weight for item in capabilities),
        "outageReady": score == 100,
        "capabilities": [asdict(item) for item in capabilities],
        "blockers": blockers,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "Platform Resilience Readiness",
        "=============================",
        f"Score: {report['score']}/{report['maximumScore']}",
        f"us-east-1 outage recovery contract ready: {'YES' if report['outageReady'] else 'NO'}",
        "",
    ]
    for item in report["capabilities"]:
        marker = "PASS" if item["status"] == "READY" else "BLOCKED"
        lines.append(f"[{marker}] {item['name']}: {item['detail']}")
    if report["blockers"]:
        lines.extend(["", "Next blockers:"])
        lines.extend(f"- {blocker}" for blocker in report["blockers"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--infra-dir", type=Path, default=Path(__file__).resolve().parents[2] / "infra")
    parser.add_argument("--terraform-outputs", type=Path)
    parser.add_argument("--json", action="store_true", help="Print JSON instead of the concise text report")
    parser.add_argument("--report", type=Path, help="Optional path for the JSON report")
    args = parser.parse_args()

    try:
        outputs = json.loads(args.terraform_outputs.read_text()) if args.terraform_outputs else terraform_outputs(args.infra_dir)
        report = assess(outputs)
    except (KeyError, OSError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"MS-017 readiness assessment could not complete: {exc}", file=sys.stderr)
        return 2

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
