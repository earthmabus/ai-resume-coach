from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_disabled_analysis_buttons_explain_all_requirements():
    html = (ROOT / "frontend" / "resume-analysis.html").read_text()
    script = (ROOT / "frontend" / "app.js").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert 'id="analyzeButtonTooltip"' in html
    assert 'id="uploadButtonTooltip"' in html
    assert 'choose a Target Career' in script
    assert 'specify a Resume name' in script
    assert 'paste resume text' in script
    assert 'upload a PDF' in script
    assert 'resumeName, textarea, fileInput' in script
    assert '.disabled-action-tooltip::after' in styles


def test_history_stacks_resume_below_target_career_and_moves_preview_up():
    script = (ROOT / "frontend" / "app.js").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()
    history = script[script.index("function renderResumeHistory"):script.index("function renderJobMatchHistory")]

    assert 'resume-history-main-grid' in history
    assert 'resume-history-left-stack' in history
    assert history.index('<span class="analysis-context-label">Target Career</span>') < history.index('<span class="analysis-context-label">Resume</span>') < history.index('resume-history-controls-panel')
    assert history.index('resume-history-left-stack') < history.index('resume-history-right')
    assert '.resume-history-main-grid .resume-history-right' in styles
    assert 'grid-row: 1' in styles


def test_dashboard_quick_stats_include_target_careers():
    html = (ROOT / "frontend" / "dashboard.html").read_text()
    script = (ROOT / "frontend" / "dashboard.js").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert '<span class="stat-label">Target Careers</span>' in html
    assert 'fetch(`${API_BASE_URL}/target-careers`' in script
    assert 'targetCareersData.targetCareers' in script
    assert 'renderStats(targetCareers, analyses, matches)' in script
    assert 'repeat(4, minmax(0, 1fr))' in styles
