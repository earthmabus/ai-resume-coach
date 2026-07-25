from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_target_career_actions_are_compact_and_refresh_is_primary():
    html = (ROOT / "frontend" / "target-career.html").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert 'id="refreshTargetCareersButton" type="button"' in html
    assert 'id="refreshTargetCareersButton" type="button" class="secondary-button"' not in html
    assert '.card-actions {' in styles
    assert 'display: flex' in styles
    assert '.target-career-form-actions {' in styles
    assert 'width: auto' in styles
    assert 'flex: 0 0 auto' in styles
