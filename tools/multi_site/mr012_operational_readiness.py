#!/usr/bin/env python3
"""MR-012 non-mutating multi-site operational-readiness preflight."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    region: str | None = None

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


def run_json(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout or "{}")


def terraform_outputs(infra_dir: Path) -> dict[str, Any]:
    return run_json(["terraform", f"-chdir={infra_dir}", "output", "-json"])


def value(outputs: dict[str, Any], key: str) -> Any:
    entry = outputs.get(key)
    if not isinstance(entry, dict) or "value" not in entry:
        raise KeyError(f"Terraform output is missing: {key}")
    return entry["value"]


def aws_command(profile: str | None, *args: str) -> list[str]:
    command = ["aws"]
    if profile:
        command += ["--profile", profile]
    command += list(args)
    return command


def http_json(url: str, timeout: int = 20) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(url, headers={"User-Agent": "mr012-readiness/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body or "{}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            payload = {"body": body[:500]}
        return exc.code, payload


def evaluate_health(site: str, expected_region: str, status: int, payload: dict[str, Any]) -> Check:
    observed = (
        payload.get("currentRegion")
        or payload.get("region")
        or (payload.get("regionalHealth") or {}).get("currentRegion")
    )
    ready = payload.get("ready")
    if status == 200 and observed == expected_region and ready is not False:
        return Check(f"{site}.api.readiness", "PASS", f"HTTP 200 from {observed}", expected_region)
    return Check(
        f"{site}.api.readiness",
        "FAIL",
        f"expected HTTP 200 from {expected_region}; received HTTP {status} from {observed or 'unknown'}",
        expected_region,
    )


def evaluate_schedule(site: str, region: str, expected_name: str, payload: dict[str, Any]) -> Check:
    state = payload.get("State")
    name = payload.get("Name")
    if name == expected_name and state == "ENABLED":
        return Check(f"{site}.publisher.schedule", "PASS", f"{name} is ENABLED", region)
    return Check(
        f"{site}.publisher.schedule",
        "FAIL",
        f"expected {expected_name} ENABLED; received name={name!r}, state={state!r}",
        region,
    )


def evaluate_lambda(site: str, component: str, region: str, expected_name: str, payload: dict[str, Any]) -> Check:
    config = payload.get("Configuration") or {}
    name = config.get("FunctionName")
    state = config.get("State")
    update = config.get("LastUpdateStatus")
    if name == expected_name and state in (None, "Active") and update in (None, "Successful"):
        return Check(f"{site}.{component}.lambda", "PASS", f"{name} is active", region)
    return Check(
        f"{site}.{component}.lambda",
        "FAIL",
        f"expected active {expected_name}; received name={name!r}, state={state!r}, update={update!r}",
        region,
    )


def evaluate_queue(site: str, queue_kind: str, region: str, queue_url: str, payload: dict[str, Any]) -> Check:
    arn = (payload.get("Attributes") or {}).get("QueueArn")
    if queue_url and arn:
        return Check(f"{site}.{queue_kind}.queue", "PASS", f"queue exists: {arn}", region)
    return Check(f"{site}.{queue_kind}.queue", "FAIL", "queue URL or ARN was missing", region)


def evaluate_table(table_name: str, primary_region: str, required_regions: set[str], witness_region: str, payload: dict[str, Any]) -> list[Check]:
    table = payload.get("Table") or {}
    status = table.get("TableStatus")
    checks = [
        Check(
            "dynamodb.table",
            "PASS" if table.get("TableName") == table_name and status == "ACTIVE" else "FAIL",
            f"table={table.get('TableName')!r}, status={status!r}",
        )
    ]

    replicas = {
        replica.get("RegionName"): replica.get("ReplicaStatus")
        for replica in table.get("Replicas", [])
        if replica.get("RegionName")
    }
    if status == "ACTIVE":
        replicas.setdefault(primary_region, "ACTIVE")
    missing = sorted(region for region in required_regions if replicas.get(region) != "ACTIVE")
    checks.append(
        Check(
            "dynamodb.active-replicas",
            "PASS" if not missing else "FAIL",
            f"active replicas={sorted(region for region, state in replicas.items() if state == 'ACTIVE')}; missing={missing}",
        )
    )

    witness = table.get("MultiRegionConsistency") == "STRONG" and bool(witness_region)
    checks.append(
        Check(
            "dynamodb.mrsc-contract",
            "PASS" if witness else "WARN",
            f"consistency={table.get('MultiRegionConsistency')!r}, configured witness={witness_region}",
            witness_region,
        )
    )
    return checks


def build_report(
    outputs: dict[str, Any],
    profile: str | None,
    runner: Callable[[list[str]], dict[str, Any]] = run_json,
    health_reader: Callable[[str, int], tuple[int, dict[str, Any]]] = http_json,
) -> dict[str, Any]:
    foundations = value(outputs, "regional_foundations")
    endpoints = value(outputs, "regional_api_endpoints")
    data = value(outputs, "resume_analysis_data")
    checks: list[Check] = []

    for site in ("east", "west"):
        foundation = foundations[site]
        region = foundation["routing"]["current_region"]
        endpoint = endpoints[site].rstrip("/")
        status, payload = health_reader(f"{endpoint}/health/ready", 20)
        checks.append(evaluate_health(site, region, status, payload))

        schedule = foundation["outbox_publisher_schedule"]
        schedule_payload = runner(
            aws_command(profile, "events", "describe-rule", "--region", region, "--name", schedule["name"], "--output", "json")
        )
        checks.append(evaluate_schedule(site, region, schedule["name"], schedule_payload))

        for component in ("api", "worker", "outbox_publisher"):
            name = foundation["compute"][component]["name"]
            lambda_payload = runner(
                aws_command(profile, "lambda", "get-function", "--region", region, "--function-name", name, "--output", "json")
            )
            checks.append(evaluate_lambda(site, component, region, name, lambda_payload))

        for queue_kind, output_key in (
            ("processing", "processing_queue"),
            ("processing-dlq", "processing_dlq"),
            ("terminal-failure-dlq", "terminal_failure_dlq"),
        ):
            queue_url = foundation[output_key]["url"]
            queue_payload = runner(
                aws_command(profile, "sqs", "get-queue-attributes", "--region", region, "--queue-url", queue_url, "--attribute-names", "QueueArn", "--output", "json")
            )
            checks.append(evaluate_queue(site, queue_kind, region, queue_url, queue_payload))

    table_name = data["table_name"]
    primary_region = data["primary_region"]
    table_payload = runner(
        aws_command(profile, "dynamodb", "describe-table", "--region", primary_region, "--table-name", table_name, "--output", "json")
    )
    checks.extend(
        evaluate_table(
            table_name,
            primary_region,
            set(data["replica_regions"]),
            data["witness_region"],
            table_payload,
        )
    )

    failures = [check for check in checks if check.status == "FAIL"]
    warnings = [check for check in checks if check.status == "WARN"]
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "result": "PASS" if not failures else "FAIL",
        "summary": {
            "total": len(checks),
            "passed": sum(check.status == "PASS" for check in checks),
            "warnings": len(warnings),
            "failed": len(failures),
        },
        "checks": [asdict(check) for check in checks],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--infra-dir", type=Path, default=Path(__file__).resolve().parents[2] / "infra")
    parser.add_argument("--terraform-outputs", type=Path, help="Use an existing terraform output -json file")
    parser.add_argument("--report", type=Path, help="Write the machine-readable report here")
    parser.add_argument("--aws-profile", default=os.environ.get("AWS_PROFILE"))
    args = parser.parse_args()

    try:
        outputs = json.loads(args.terraform_outputs.read_text()) if args.terraform_outputs else terraform_outputs(args.infra_dir)
        report = build_report(outputs, args.aws_profile)
    except (subprocess.CalledProcessError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"MR-012 preflight could not complete: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n")
    print(rendered)
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
