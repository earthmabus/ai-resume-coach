from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_history_context_and_preview_use_equal_columns_without_overlap():
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert "grid-template-columns: 50px minmax(0, 1fr) minmax(0, 1fr)" in styles
    assert ".resume-history-main-grid .resume-history-left-stack" in styles
    assert "grid-column: 2" in styles
    assert ".resume-history-main-grid .resume-history-right" in styles
    assert "grid-column: 3" in styles
    assert "align-self: stretch" in styles
    assert "max-width: 100%" in styles


def test_history_preview_stretches_to_controls_bottom():
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert ".resume-history-main-grid .resume-history-right > .pdf-thumbnail" in styles
    assert ".resume-history-main-grid .resume-history-right > .resume-preview" in styles
    assert "height: 100%" in styles
    assert "min-height: 230px" in styles
    assert "max-height: none" in styles


def test_target_career_cards_use_dashboard_style_hover_lift():
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert ".target-career-card:hover" in styles
    assert ".target-career-card:focus-within" in styles
    assert "transform: translateY(-4px)" in styles
    assert "transition: transform 160ms ease, box-shadow 160ms ease" in styles
    assert "@media (prefers-reduced-motion: reduce)" in styles
