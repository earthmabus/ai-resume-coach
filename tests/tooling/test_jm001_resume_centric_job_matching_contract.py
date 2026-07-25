from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "frontend" / "job-matching.html").read_text()
SCRIPT = (ROOT / "frontend" / "app.js").read_text()
STYLES = (ROOT / "frontend" / "styles.css").read_text()


def test_job_matching_replaces_resume_dropdown_with_selectable_resume_cards():
    assert 'id="resumeAnalysisSelect"' not in HTML
    assert 'id="jobResumeList"' in HTML
    assert 'class="job-resume-grid"' in HTML
    assert "function renderJobResumeCards" in SCRIPT
    assert "jobResumeCardMarkup" in SCRIPT
    assert 'name="jobResumeAnalysis"' in SCRIPT
    assert "selectedJobResumeAnalysisId" in SCRIPT
    assert "job-resume-option.selected" in STYLES


def test_resume_cards_show_resume_context_and_analysis_quality():
    assert 'item.resumeName || "Untitled Resume"' in SCRIPT
    assert "item.fileName" in SCRIPT
    assert "analysisTargetCareer(item)" in SCRIPT
    assert "targetCareerVersionLabel(career)" in SCRIPT
    assert "job-resume-score" in SCRIPT
    assert "Analyzed" in SCRIPT


def test_job_match_submission_uses_selected_resume_card():
    match_section = SCRIPT[
        SCRIPT.index("async function matchJobDescription"):
        SCRIPT.index("async function loadJobMatches")
    ]
    assert 'selectedJobResumeAnalysisId || resumeAnalysisSelect?.value || ""' in match_section
    assert "Select a resume analysis first." in match_section


def test_job_match_result_uses_score_and_context_panels():
    section = SCRIPT[
        SCRIPT.index("function renderJobMatch(data"):
        SCRIPT.index("function completedResumeAnalyses")
    ]
    assert "job-match-result-header-grid" in section
    assert "job-match-score-panel" in section
    assert "jobMatchContextMarkup(data" in section
    assert "Job Match Complete" not in section
    assert "<strong>Created:</strong>" not in section
    assert "score-good" in STYLES
    assert "score-warning" in STYLES
    assert "score-poor" in STYLES


def test_job_match_history_matches_resume_history_visual_language():
    section = SCRIPT[
        SCRIPT.index("function renderJobMatchHistory"):
        SCRIPT.index("function renderResumeTailoring")
    ]
    assert "job-match-history-grid" in section
    assert "job-match-history-score" in section
    assert 'analysis-context-label">Job' in section
    assert 'analysis-context-label">Resume' in section
    assert "jobDescriptionText.slice" in section
    assert "presentation.historyLabel" in section
    assert "toggleCardDetails" not in section
    assert "<strong>Created:</strong>" not in section
    assert "<strong>Match Score:</strong>" not in section
    assert "job-match-history-grid" in STYLES
