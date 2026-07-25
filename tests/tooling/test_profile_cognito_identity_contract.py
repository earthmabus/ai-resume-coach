from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_profile_page_uses_cognito_identity_fields_only():
    html = (ROOT / "frontend" / "profile.html").read_text()

    assert 'id="firstName"' in html
    assert 'id="lastName"' in html
    assert 'id="emailAddress"' in html
    assert 'id="preferredProvider"' in html
    assert 'id="saveProfileButton"' in html
    assert 'id="emailAddress" type="email"' in html
    assert "readonly" in html


def test_profile_script_uses_token_claims_and_cognito_when_available():
    script = (ROOT / "frontend" / "profile.js").read_text()

    assert "claimsFromSession" in script
    assert "claims.email" in script
    assert "claims.given_name" in script
    assert "claims.family_name" in script
    assert "getUserAttributes" in script
    assert "updateAttributes" in script
    assert 'Name: "given_name"' in script
    assert 'Name: "family_name"' in script


def test_profile_explicitly_attaches_restored_session():
    script = (ROOT / "frontend" / "profile.js").read_text()

    assert "user.setSignInUserSession(session);" in script
    assert "async function getAuthenticatedCognitoContext()" in script


def test_profile_persists_legacy_name_fallback_in_application_profile():
    script = (ROOT / "frontend" / "profile.js").read_text()
    backend = (ROOT / "src" / "features" / "profile.py").read_text()

    assert "firstName: firstNameInput.value.trim()" in script
    assert "lastName: lastNameInput.value.trim()" in script
    assert '"firstName": str(item.get("firstName") or "")' in backend
    assert '"lastName": str(item.get("lastName") or "")' in backend
    assert '"firstName = :firstName, "' in backend
    assert '"lastName = :lastName, "' in backend


def test_cognito_attribute_failure_does_not_break_profile_page():
    script = (ROOT / "frontend" / "profile.js").read_text()

    assert 'console.warn("Could not refresh Cognito user attributes"' in script
    assert 'console.warn("Profile saved, but Cognito name sync failed"' in script


def test_profile_asset_version_is_bumped_for_resilient_identity_fix():
    html = (ROOT / "frontend" / "profile.html").read_text()

    assert './profile.js?v=5' in html
