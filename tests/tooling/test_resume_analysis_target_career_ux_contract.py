from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_resume_analysis_requires_explicit_target_career_selection():
    html = (ROOT / "frontend" / "resume-analysis.html").read_text()
    script = (ROOT / "frontend" / "app.js").read_text()

    assert "Choose a Target Career" in html
    assert 'id="resumeTargetCareerList"' in html
    assert "loadResumeTargetCareers" in script
    assert "targetCareerId: targetCareer.targetCareerId" in script
    assert "Choose a Target Career before analyzing your resume." in script


def test_resume_analysis_assets_are_cache_busted_for_ra003():
    html = (ROOT / "frontend" / "resume-analysis.html").read_text()

    assert "./styles.css?v=26" in html
    assert "./app.js?v=24" in html
