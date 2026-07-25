from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_target_career_ai_assist_is_between_summary_and_details():
    html = (ROOT / "frontend" / "target-career.html").read_text()
    assert html.index('id="careerGoalSummary"') < html.index('id="generateTargetCareerDetailsButton"')
    assert html.index('id="generateTargetCareerDetailsButton"') < html.index('for="keyResponsibilities"')
    assert "Generate career details with AI" in html


def test_target_career_generation_is_async_and_polled():
    script = (ROOT / "frontend" / "target-career.js").read_text()
    assert '/target-careers/generate-details`' in script
    assert '/target-careers/generations/${encodeURIComponent(activeGenerationId)}`' in script
    assert "GENERATION_POLL_INTERVAL_MS" in script
    assert "AI is drafting your career details" in script


def test_generated_fields_are_reviewable_and_not_auto_saved():
    script = (ROOT / "frontend" / "target-career.js").read_text()
    assert "applyGeneratedDetails(data)" in script
    assert "saveTargetCareer()" not in script[script.index("function applyGeneratedDetails"):script.index("async function pollTargetCareerGeneration")]
    assert "Replace them with a new AI-generated draft" in script


def test_generation_ui_has_explicit_idle_processing_and_completed_states():
    script = (ROOT / "frontend" / "target-career.js").read_text()
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert 'function setGenerationState(state, message = "")' in script
    assert 'resetGenerationState();' in script
    assert 'setGenerationState("completed")' in script
    assert 'GENERATION_SUCCESS_DISPLAY_MS' in script
    assert '.target-career-generation-status.hidden' in styles
    assert 'display: none;' in styles[styles.index('.target-career-generation-status.hidden'):styles.index('.target-career-generation-status.is-complete')]


def test_editing_existing_career_resets_generation_ui_and_polling():
    script = (ROOT / "frontend" / "target-career.js").read_text()
    edit_block = script[script.index("function openEditEditor"):script.index("function closeEditor")]

    assert "resetGenerationState();" in edit_block
    assert 'if (activeGenerationId) return;' in script
    assert 'activeGenerationStatuses.has(status)' in script


def test_target_career_assets_are_bumped_for_tc002():
    html = (ROOT / "frontend" / "target-career.html").read_text()
    assert "./styles.css?v=9" in html
    assert "./target-career.js?v=8" in html
