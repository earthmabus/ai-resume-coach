from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_public_splash_and_protected_dashboard_are_separate():
    splash = (ROOT / "frontend" / "index.html").read_text()
    dashboard = (ROOT / "frontend" / "dashboard.html").read_text()
    login = (ROOT / "frontend" / "login.js").read_text()
    assert "Build momentum for" in splash
    assert "Our purpose" in splash
    assert "Start building momentum" in splash
    assert "Quick Stats" in dashboard
    assert './dashboard.html' in login

def test_momentum_theme_and_resume_card_alignment_contract():
    css = (ROOT / "frontend" / "styles.css").read_text()
    assert "--orange: #f05a19" in css
    assert ".landing-hero" in css
    assert ".job-resume-grid { align-items:stretch; grid-auto-rows:1fr; }" in css
    assert ".job-resume-option { height:100%;" in css
    assert ".job-resume-grid > label.job-resume-option" in css
    assert "margin: 0;" in css
    job_html = (ROOT / "frontend" / "job-matching.html").read_text()
    assert './styles.css?v=27' in job_html

def test_landing_hero_rotates_between_launch_and_results_every_ten_seconds():
    splash = (ROOT / "frontend" / "index.html").read_text()
    script = (ROOT / "frontend" / "landing.js").read_text()
    css = (ROOT / "frontend" / "styles.css").read_text()

    assert 'data-hero-scene' in splash
    assert 'hero-scene-rocket' in splash
    assert 'hero-scene-results' in splash
    assert './landing.js?v=1' in splash
    assert 'window.setInterval' in script
    assert '10000' in script
    assert 'prefers-reduced-motion: reduce' in css
    assert '.momentum-rocket' in css
