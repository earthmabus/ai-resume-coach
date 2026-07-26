from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_history_tags_and_actions_are_grouped_under_target_career():
    script = (ROOT / "frontend" / "app.js").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()
    history = script[script.index("function renderResumeHistory"):script.index("function renderJobMatchHistory")]

    assert '<div class="resume-history-controls-panel">' in history
    assert history.index('resume-history-controls-panel') < history.index('resume-history-right')
    assert 'item.sourceType || "unknown"' not in history
    assert '.resume-history-left-stack' in styles
    assert '.resume-history-controls-panel .button-row' in styles
    assert 'background: transparent' in styles
    assert 'border: 0' in styles
    assert 'padding: 0' in styles
    assert '.resume-history-right .resume-preview.small-preview' in styles
    assert 'height: 230px' in styles


def test_history_asset_versions_are_bumped():
    html = (ROOT / "frontend" / "resume-analysis.html").read_text()
    assert './styles.css?v=26' in html
    assert './app.js?v=24' in html
