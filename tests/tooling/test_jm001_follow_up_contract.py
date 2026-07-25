from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_job_match_submission_is_gated_with_tooltip():
    html = (ROOT / "frontend" / "job-matching.html").read_text()
    script = (ROOT / "frontend" / "app.js").read_text()

    assert 'id="matchJobButtonTooltip"' in html
    assert 'id="matchJobButton" disabled' in html
    assert "function jobMatchMissingRequirements()" in script
    assert 'missing.push("a job name")' in script
    assert 'missing.push("a URL")' in script
    assert 'missing.push("a job description")' in script
    assert 'missing.push("a resume")' in script
    assert "updateJobMatchAvailability" in script


def test_resume_cards_and_score_layouts_are_contained():
    styles = (ROOT / "frontend" / "styles.css").read_text()

    assert ".job-resume-grid" in styles
    assert "grid-auto-rows: 1fr" in styles
    assert ".job-resume-option" in styles
    assert "height: 100%" in styles
    assert ".job-match-score-panel" in styles
    assert "aspect-ratio: 1 / 1" in styles
    assert "overflow: hidden" in styles
    assert "grid-template-columns: 82px minmax(0, 1fr) minmax(0, 1fr)" in styles
