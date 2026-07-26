import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "resilience" / "platform_readiness.py"
SPEC = importlib.util.spec_from_file_location("ms017_platform_readiness", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def wrapped(value):
    return {"value": value}


def outputs(*, routing=False, health=False, identity=False, documents=False):
    result = {
        "regional_sites": wrapped(
            {
                "east": {"region": "us-east-1"},
                "west": {"region": "us-west-2"},
            }
        ),
        "resume_analysis_data": wrapped(
            {
                "replica_regions": ["us-east-1", "us-west-2"],
                "witness_region": "us-east-2",
                "consistency_mode": "STRONG",
            }
        ),
        "global_api_routing": wrapped(
            {"enabled": routing, "health_checks_enabled": health}
        ),
        "regional_foundations": wrapped(
            {
                "east": {"document_bucket": {"name": "east-documents"}},
                "west": {"document_bucket": {"name": "west-documents"}},
            }
        ),
    }
    if identity:
        result["cognito_recovery"] = wrapped({"enabled": True, "mode": "WARM_STANDBY_RESET_REQUIRED", "password_continuity": False, "session_continuity": False, "automated_failover": False})
    if documents:
        result["document_replication"] = wrapped({"enabled": True})
    return result


def test_current_baseline_scores_mrsc_and_regional_sites_only():
    report = MODULE.assess(outputs())
    assert report["score"] == 45
    assert report["outageReady"] is False
    blocked = {
        item["name"] for item in report["capabilities"] if item["status"] == "BLOCKED"
    }
    assert blocked == {
        "global_api_latency_routing",
        "route53_health_checks",
        "identity_recovery",
        "document_continuity",
    }


def test_complete_contract_is_outage_ready():
    report = MODULE.assess(outputs(routing=True, health=True, identity=True, documents=True))
    assert report["score"] == 100
    assert report["outageReady"] is True
    assert report["blockers"] == []


def test_text_report_is_concise_and_names_outage_readiness():
    rendered = MODULE.render_text(MODULE.assess(outputs(routing=True)))
    assert "Score: 65/100" in rendered
    assert "us-east-1 outage recovery contract ready: NO" in rendered
    assert "[PASS] global_api_latency_routing" in rendered
    assert "[BLOCKED] route53_health_checks" in rendered


def test_wrapper_is_read_only():
    text = (ROOT / "tools" / "resilience" / "platform_readiness.sh").read_text()
    for forbidden in ("terraform apply", "aws ", "enable-rule", "update-"):
        assert forbidden not in text
