import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "multi_site" / "mr012_operational_readiness.py"
SPEC = importlib.util.spec_from_file_location("mr012_operational_readiness", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def outputs():
    def wrapped(value):
        return {"value": value}

    foundations = {}
    endpoints = {}
    for site, region in (("east", "us-east-1"), ("west", "us-west-2")):
        prefix = "use1" if site == "east" else "usw2"
        foundations[site] = {
            "routing": {"current_region": region},
            "outbox_publisher_schedule": {"name": f"app-{prefix}-publisher"},
            "compute": {
                "api": {"name": f"app-{prefix}-api"},
                "worker": {"name": f"app-{prefix}-worker"},
                "outbox_publisher": {"name": f"app-{prefix}-publisher"},
            },
            "processing_queue": {"url": f"https://sqs.{region}.amazonaws.com/1/{prefix}-processing"},
            "processing_dlq": {"url": f"https://sqs.{region}.amazonaws.com/1/{prefix}-dlq"},
            "terminal_failure_dlq": {"url": f"https://sqs.{region}.amazonaws.com/1/{prefix}-terminal"},
        }
        endpoints[site] = f"https://{site}.example.test"

    return {
        "regional_foundations": wrapped(foundations),
        "regional_api_endpoints": wrapped(endpoints),
        "resume_analysis_data": wrapped(
            {
                "table_name": "resume-analysis",
                "primary_region": "us-east-1",
                "replica_regions": ["us-east-1", "us-west-2"],
                "witness_region": "us-east-2",
            }
        ),
    }


def healthy_runner(command):
    if "describe-rule" in command:
        name = command[command.index("--name") + 1]
        return {"Name": name, "State": "ENABLED"}
    if "get-function" in command:
        name = command[command.index("--function-name") + 1]
        return {"Configuration": {"FunctionName": name, "State": "Active", "LastUpdateStatus": "Successful"}}
    if "get-queue-attributes" in command:
        return {"Attributes": {"QueueArn": "arn:aws:sqs:region:account:queue"}}
    if "describe-table" in command:
        return {
            "Table": {
                "TableName": "resume-analysis",
                "TableStatus": "ACTIVE",
                "MultiRegionConsistency": "STRONG",
                "Replicas": [
                    {"RegionName": "us-east-1", "ReplicaStatus": "ACTIVE"},
                    {"RegionName": "us-west-2", "ReplicaStatus": "ACTIVE"},
                ],
            }
        }
    raise AssertionError(command)


def healthy_http(url, timeout):
    region = "us-east-1" if "east" in url else "us-west-2"
    return 200, {"ready": True, "currentRegion": region}


def test_build_report_passes_for_ready_platform():
    report = MODULE.build_report(outputs(), None, healthy_runner, healthy_http)
    assert report["result"] == "PASS"
    assert report["summary"]["failed"] == 0
    assert report["summary"]["passed"] >= 15


def test_disabled_publisher_fails_preflight():
    def runner(command):
        payload = healthy_runner(command)
        if "describe-rule" in command and "us-west-2" in command:
            payload["State"] = "DISABLED"
        return payload

    report = MODULE.build_report(outputs(), None, runner, healthy_http)
    assert report["result"] == "FAIL"
    failed = {item["name"] for item in report["checks"] if item["status"] == "FAIL"}
    assert "west.publisher.schedule" in failed


def test_wrong_health_region_fails_preflight():
    def http(url, timeout):
        return 200, {"ready": True, "currentRegion": "us-east-1"}

    report = MODULE.build_report(outputs(), None, healthy_runner, http)
    failed = {item["name"] for item in report["checks"] if item["status"] == "FAIL"}
    assert "west.api.readiness" in failed


def test_wrapper_is_non_mutating_and_writes_evidence():
    text = (ROOT / "tools" / "multi_site" / "mr012_operational_readiness.sh").read_text()
    assert "new_evidence_dir \"mr012\"" in text
    assert "report.json" in text
    assert "confirm_mutation" not in text
    for forbidden in ("put-function", "update-event-source", "disable-rule", "enable-rule"):
        assert forbidden not in text
