from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_JS = REPO_ROOT / "frontend" / "app.js"
JOB_MATCHING_HTML = REPO_ROOT / "frontend" / "job-matching.html"


def test_job_matching_uses_friendly_status_presentations():
    source = APP_JS.read_text(encoding="utf-8")

    assert "JOB_MATCH_STATUS_PRESENTATION" in source
    assert "Preparing your job match" in source
    assert "Comparing your resume with the job" in source
    assert "QUEUED_PENDING_DISPATCH" not in JOB_MATCHING_HTML.read_text(encoding="utf-8")


def test_job_matching_transitions_to_result_and_polls_automatically():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'transitionToJobMatchResult()' in source
    assert 'setAccordionOpen("matchJobCard", false)' in source
    assert 'focusAccordionCard("jobResultCard", true)' in source
    assert "JOB_MATCH_POLL_DELAYS_MS = [0, 2000, 4000, 6000, 10000]" in source
    assert "JOB_MATCH_POLL_TIMEOUT_MS = 5 * 60 * 1000" in source
    assert "pollJobMatchUntilComplete(matchId)" in source


def test_job_match_history_refreshes_and_resumes_active_work():
    source = APP_JS.read_text(encoding="utf-8")

    assert "resumeActiveMatch" in source
    assert "isJobMatchInProgress(item.status)" in source
    assert "loadJobMatches({ resumeActiveMatch: false })" in source
    assert "jobMatchStatusPresentation(item.status).historyLabel" in source


def test_job_matching_cache_buster_is_updated():
    html = JOB_MATCHING_HTML.read_text(encoding="utf-8")
    assert '<script src="./app.js?v=10"></script>' in html
