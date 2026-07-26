from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_target_career_grid_caps_desktop_layout_at_three_columns():
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert ".target-career-grid" in styles
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in styles
    assert "@media (max-width: 1100px)" in styles
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in styles


def test_target_career_card_actions_are_adjacent_and_use_expected_styles():
    script = (ROOT / "frontend" / "target-career.js").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert 'class="edit-target-career"' in script
    assert 'class="secondary-button delete-target-career"' in script
    assert 'class="danger-button delete-target-career"' not in script
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in styles


def test_career_goal_summary_precedes_key_responsibilities():
    html = (ROOT / "frontend" / "target-career.html").read_text()

    assert html.index('for="careerGoalSummary"') < html.index('for="keyResponsibilities"')


def test_editor_actions_share_one_row_and_top_cancel_is_removed():
    html = (ROOT / "frontend" / "target-career.html").read_text()
    script = (ROOT / "frontend" / "target-career.js").read_text()

    assert 'class="form-actions target-career-form-actions"' in html
    assert html.index('id="saveTargetCareerButton"') < html.index('id="cancelTargetCareerButtonBottom"')
    assert 'id="cancelTargetCareerButton"' not in html
    assert 'getElementById("cancelTargetCareerButton")' not in script


def test_target_career_cards_hide_environment_and_use_last_updated_label():
    script = (ROOT / "frontend" / "target-career.js").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert "<dt>Environment</dt>" not in script
    assert "Last Updated" in script
    assert 'class="last-updated-label"' in script
    assert ".last-updated-label" in styles
    assert "font-style: italic;" in styles
    assert "font-weight: 400;" in styles


def test_target_career_assets_are_cache_busted_for_refinement():
    html = (ROOT / "frontend" / "target-career.html").read_text()

    assert "./styles.css?v=26" in html
    assert "./target-career.js?v=8" in html
