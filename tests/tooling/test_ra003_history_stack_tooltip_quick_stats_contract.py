from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_history_resume_panel_is_forced_below_target_career():
    styles = (ROOT / "frontend" / "styles.css").read_text()
    assert "grid-template-columns: minmax(0, 1fr) !important" in styles
    assert ".resume-history-left-stack > .analysis-context-panel" in styles


def test_disabled_action_tooltips_are_not_clipped_or_centered_offscreen():
    styles = (ROOT / "frontend" / "styles.css").read_text()
    assert "#analyzeResumeCard" in styles
    assert "overflow: visible" in styles
    assert "#analyzeResumeCard .disabled-action-tooltip::after" in styles
    assert "left: 0" in styles


def test_dashboard_has_four_stats_without_completed_matches():
    index = (ROOT / "frontend" / "index.html").read_text()
    dashboard = (ROOT / "frontend" / "dashboard.js").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()
    assert "Completed Matches" not in index
    assert "completedMatches" not in dashboard
    assert "repeat(4, minmax(0, 1fr))" in styles
