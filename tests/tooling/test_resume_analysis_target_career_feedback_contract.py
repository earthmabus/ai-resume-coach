from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_target_career_cards_show_version_and_last_updated_without_fixed_whitespace():
    script = (ROOT / "frontend" / "app.js").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert "targetCareerVersionLabel" in script
    assert "Last Updated" in script
    assert "align-items: stretch" in styles
    assert "box-sizing: border-box" in styles
    assert ".resume-target-career-option {\n  height: 100%" not in styles


def test_analysis_actions_require_target_career_selection():
    html = (ROOT / "frontend" / "resume-analysis.html").read_text()
    script = (ROOT / "frontend" / "app.js").read_text()

    assert 'id="analyzeButton" disabled' in html
    assert 'id="uploadButton" disabled' in html
    assert "updateResumeAnalysisAvailability" in script
    assert "analyzeButton.disabled = !textReady" in script
    assert "uploadButton.disabled = !pdfReady" in script


def test_no_target_careers_hides_resume_inputs():
    html = (ROOT / "frontend" / "resume-analysis.html").read_text()
    script = (ROOT / "frontend" / "app.js").read_text()

    assert 'id="resumeAnalysisInputs" class="hidden"' in html
    assert 'resumeAnalysisInputs?.classList.toggle("hidden", !hasCareers)' in script
    assert "Create a Target Career first" in html


def test_result_hero_uses_ats_score_and_stacked_context_panels():
    script = (ROOT / "frontend" / "app.js").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert "ATS Score" in script
    assert 'analysisContextPanelMarkup(data, "vertical")' in script
    assert "Resume Analysis Complete" not in script
    assert 'Status: ${escapeHtml(analysisStatusPresentation(status).historyLabel)}' not in script
    assert "Created: ${escapeHtml(formatEastern(data.createdAt))}" in script
    assert ".analysis-result-hero" in styles
    assert ".analysis-context-panels.vertical" in styles


def test_history_uses_separate_horizontal_context_panels_and_pdf_thumbnail():
    script = (ROOT / "frontend" / "app.js").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert "resume-history-main-grid" in script
    assert "history-score-cell" in script
    assert "hydrateResumePdfPreviews" in script
    assert "data-pdf-analysis-id" in script
    assert "#page=1&view=FitH" in script
    assert ".analysis-context-panels.horizontal" in styles
    assert ".pdf-thumbnail-frame" in styles
