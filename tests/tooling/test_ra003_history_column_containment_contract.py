from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_history_context_panels_are_contained_inside_left_column():
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert ".resume-history-main-grid .analysis-context-panel," in styles
    assert ".resume-history-main-grid .resume-history-controls-panel {" in styles
    assert "box-sizing: border-box;" in styles
    assert ".resume-history-main-grid .resume-history-left-stack {" in styles
    assert "overflow: hidden;" in styles
    assert "max-width: 100%;" in styles


def test_resume_analysis_uses_latest_stylesheet_version():
    html = (ROOT / "frontend" / "resume-analysis.html").read_text()
    assert './styles.css?v=31' in html



def test_resume_analysis_header_context_cannot_overlap_score_column():
    script = (ROOT / "frontend" / "app.js").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()
    html = (ROOT / "frontend" / "resume-analysis.html").read_text()

    assert 'class="analysis-result-context"' in script
    assert "grid-template-columns: var(--analysis-score-panel-size) minmax(0, 1fr)" in styles
    assert ".analysis-result-header-grid > .analysis-result-context" in styles
    assert "min-width: 0;" in styles
    assert "max-width: 100%;" in styles
    assert "overflow: hidden;" in styles
    assert './app.js?v=26' in html
