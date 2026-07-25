from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_result_score_panel_is_white_and_score_colored():
    script = (ROOT / "frontend" / "app.js").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert "function atsScoreToneClass(score)" in script
    assert 'return "score-good"' in script
    assert 'return "score-warning"' in script
    assert 'return "score-poor"' in script
    assert "score-circle ${atsScoreToneClass(score)}" in script
    assert "background: #ffffff" in styles
    assert ".score-circle.score-good" in styles
    assert ".score-circle.score-warning" in styles
    assert ".score-circle.score-poor" in styles


def test_history_score_has_no_enclosing_panel_and_created_is_second_tag():
    script = (ROOT / "frontend" / "app.js").read_text()
    history = script[script.index("function renderResumeHistory"):script.index("function renderJobMatchHistory")]

    assert '<div class="history-score-cell">' in history
    assert '<div class="analysis-score-panel compact">' not in history
    assert "atsScoreToneClass(score)" in history
    metrics = history[history.index('<div class="history-metrics">'):history.index('</div>', history.index('<div class="history-metrics">'))]
    assert metrics.index("status-") < metrics.index("Created:") < metrics.index("item.provider")
    assert "item.sourceType" not in metrics
    assert 'class="history-created"' not in history


def test_history_panels_are_consistent_and_preview_returns_to_resume_column():
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert "grid-template-columns: 82px minmax(0, 1fr) minmax(0, 1fr)" in styles
    assert "grid-auto-rows: 82px" in styles
    assert ".history-score-cell" in styles
    assert "grid-column: 3" in styles


def test_result_pdf_preview_is_double_height_while_compact_preview_uses_default():
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert ".pdf-thumbnail:not(.compact)" in styles
    assert "min-height: 460px" in styles
    assert "height: 460px" in styles
    assert ".pdf-thumbnail.compact," not in styles
