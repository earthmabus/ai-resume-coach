from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_result_uses_equal_panel_grid_and_aligned_metrics():
    script = (ROOT / "frontend" / "app.js").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert "analysis-result-header-grid" in script
    assert "analysis-score-panel" in script
    assert "analysis-result-metrics" in script
    assert "grid-template-columns: auto minmax(0, 1fr)" in styles
    assert 'grid-template-areas:' in styles
    assert '<h3>Target Career</h3>' not in script
    assert '<strong>Role:</strong>' not in script
    assert '<strong>Industry:</strong>' not in script


def test_result_pdf_uses_thumbnail_preview():
    script = (ROOT / "frontend" / "app.js").read_text()

    assert "resumePreviewSectionMarkup(data" in script
    assert 'headingId: "resumePreviewHeading"' in script
    assert "Resume PDF Preview" in script
    assert "hydrateResumePdfPreviews();" in script


def test_history_uses_ats_panel_and_inline_detail_tags():
    script = (ROOT / "frontend" / "app.js").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert "resume-history-main-grid" in script
    history_section = script[script.index("function renderResumeHistory"):script.index("function renderJobMatchHistory")]
    assert "Score:</strong>" not in history_section
    assert "toggleCardDetails" not in history_section
    assert "Words:" in script
    assert "Duration:" in script
    assert "Model:" in script
    assert "Version:" in script
    assert "grid-template-columns: 50px minmax(0, 1fr) minmax(0, 1fr)" in styles
    assert "grid-column: 3" in styles
    assert "resume-history-controls-panel" in script


def test_resume_analysis_promotes_summary_and_groups_assessment_content():
    source = (ROOT / "frontend" / "app.js").read_text()

    render_start = source.index("function renderAnalysis(data)")
    render_end = source.index("function selectedResumeTargetCareer()")
    render_source = source[render_start:render_end]

    assert 'id="analysisExecutiveSummaryHeading"' in render_source
    assert render_source.index('id="analysisExecutiveSummaryHeading"') < render_source.index('id="roleSpecificScoresHeading"')
    assert 'class="result-grid role-assessment-grid"' in render_source
    assert '<h3>Role Fit Summary</h3>' in render_source
    assert '<h3>Role-Specific Gaps</h3>' in render_source
    assert 'id="strengthsRecommendationsHeading"' in render_source
