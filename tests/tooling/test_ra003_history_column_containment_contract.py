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
    assert './styles.css?v=24' in html
