import importlib.util, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'tools/multi_site/mr014_chaos_validation.py'
S=importlib.util.spec_from_file_location('mr014_enhanced',P); M=importlib.util.module_from_spec(S); sys.modules[S.name]=M; S.loader.exec_module(M)

def passing_payload():
    return {'scenarios': {s.id: {'status':'PASS','restored': bool(s.restoration),'checks': {p.replace(' ','_'): True for p in s.proves},'evidence':f'evidence/{s.id}'} for s in M.SCENARIOS}}

def test_catalog_is_end_to_end_certification():
    c=M.catalog(); assert c['schemaVersion']==2; assert c['certification']=='END_TO_END_CHAOS_AND_FAILURE'
    assert [s['id'] for s in c['scenarios']]==['guard-both-sites','bidirectional-routing','worker-backlog','post-recovery']
    assert c['safety']['routingPlanMustBeRoutingOnly'] is True

def test_certification_requires_every_scenario():
    p=passing_payload(); del p['scenarios']['post-recovery']; r=M.evaluate(p)
    assert r['result']=='FAIL'; assert r['summary']['complete'] is False

def test_certification_requires_restoration():
    p=passing_payload(); p['scenarios']['worker-backlog']['restored']=False; r=M.evaluate(p)
    assert r['result']=='FAIL'; assert any('restoration' in e for e in r['errors'])

def test_certification_rejects_false_checks():
    p=passing_payload(); p['scenarios']['bidirectional-routing']['checks']['dns_convergence']=False; r=M.evaluate(p)
    assert r['result']=='FAIL'; assert any('failed checks' in e for e in r['errors'])

def test_complete_certification_passes():
    r=M.evaluate(passing_payload()); assert r['result']=='PASS'; assert r['summary']=={'total':4,'executed':4,'passed':4,'complete':True}

def test_cli_catalog():
    out=subprocess.check_output([sys.executable,str(P),'catalog'],text=True); assert json.loads(out)['schemaVersion']==2

def test_wrapper_contains_safety_cleanup_and_e2e_assertions():
    t=(ROOT/'tools/multi_site/mr014_chaos_validation.sh').read_text()
    for token in ['EXECUTE_CHAOS','CONFIRM_MUTATION','mr009d4_runtime_validation.sh','restore_worker','duplicate_idempotent','queue_drained','certify)']:
        assert token in t


def test_latest_evidence_avoids_pipefail_sigpipe_pipeline():
    text = (ROOT / "tools/multi_site/mr014_chaos_validation.sh").read_text()
    function = text.split("latest_evidence(){", 1)[1].split("write_result(){", 1)[0]
    assert "python -" in function
    assert "head -1" not in function
    assert "sort -nr" not in function


def test_worker_claims_queued_status_in_repository_snapshot():
    worker = (ROOT / "src/lambdas/worker/handler.py").read_text()
    assert "STATUS_QUEUED," in worker
    assert "def claimable_statuses" in worker


def test_certify_uses_exact_step_evidence_directories():
    text = (ROOT / "tools/multi_site/mr014_chaos_validation.sh").read_text()
    certify = text.split(" certify)", 1)[1].split(" catalog)", 1)[0]
    assert 'mkdir -p "$EVIDENCE_DIR/steps"' in certify
    assert 'EVIDENCE_DIR_OVERRIDE="$step_evidence" "$0" "$step"' in certify
    assert 'step_results="$step_evidence/results.json"' in certify
    assert 'latest_evidence mr014-${step}' not in certify
    assert 'Missing scenario results for $step' in certify


def test_evidence_override_is_consumed_before_nested_scripts():
    text = (ROOT / "tools/multi_site/common.sh").read_text()
    function = text.split("new_evidence_dir() {", 1)[1].split("record() {", 1)[0]
    assert 'EVIDENCE_DIR="$EVIDENCE_DIR_OVERRIDE"' in function
    assert "unset EVIDENCE_DIR_OVERRIDE" in function


def test_saved_plan_apply_sanitizes_ambient_runtime_tf_vars():
    text = (ROOT / "tools/multi_site/mr009d4_runtime_validation.sh").read_text()
    command = "env -u TF_VAR_deployment_id -u TF_VAR_analysis_provider"
    assert text.count(command) == 2


def test_worker_backlog_waits_for_outbox_dispatch_instead_of_fixed_sleep():
    text = (ROOT / "tools/multi_site/mr014_chaos_validation.sh").read_text()
    worker = text.split(" worker-certification)", 1)[1].split(" post-recovery)", 1)[0]
    assert "BACKLOG_APPEAR_TIMEOUT_SECONDS" in worker
    assert "backlog-latest.json" in worker
    assert "ApproximateNumberOfMessagesNotVisible" in worker
    assert 'sleep "${BACKLOG_ACCUMULATION_SECONDS:-15}"' not in worker


def test_worker_restoration_is_confirmed_before_marking_restored():
    text = (ROOT / "tools/multi_site/mr014_chaos_validation.sh").read_text()
    worker = text.split(" worker-certification)", 1)[1].split(" post-recovery)", 1)[0]
    enabled_check = '[[ "$state" == Enabled ]] ||'
    assert enabled_check in worker
    assert worker.index(enabled_check) < worker.index("restored=1")
    assert "queue-drain-latest.json" in worker
