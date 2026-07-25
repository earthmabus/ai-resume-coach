from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_resume_and_job_results_group_related_content_into_panels():
    app = (ROOT / "frontend" / "app.js").read_text()
    assert 'aria-labelledby="roleSpecificScoresHeading"' in app
    assert 'aria-labelledby="resumePreviewHeading"' in app
    assert 'aria-labelledby="jobExecutiveSummaryHeading"' in app
    assert 'aria-labelledby="jobResumePreviewHeading"' in app
    assert app.count('class="result-section-panel') >= 4


def test_dashboard_recent_activity_uses_context_panels_and_score_circles():
    dashboard = (ROOT / "frontend" / "dashboard.js").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()
    assert 'function renderResumeActivity' in dashboard
    assert 'function renderJobActivity' in dashboard
    assert 'dashboard-score-circle' in dashboard
    assert 'analysis-context-label">Target Career' in dashboard
    assert 'analysis-context-label">Resume' in dashboard
    assert 'analysis-context-label">Job' in dashboard
    assert 'dashboard-context-grid' in styles
    assert 'grid-template-columns: repeat(2, minmax(0, 1fr));' in styles
    assert 'pdf-thumbnail' not in dashboard
    assert 'resume-preview' not in dashboard
