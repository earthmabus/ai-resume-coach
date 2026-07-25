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

    for removed_id in (
        "profileName",
        "currentTitle",
        "targetTitle",
        "yearsExperience",
        "certifications",
        "resumeStyle",
    ):
        assert f'id="{removed_id}"' not in html


def test_profile_script_sources_identity_from_cognito():
    script = (ROOT / "frontend" / "profile.js").read_text()

    assert "getUserAttributes" in script
    assert 'attributes.given_name' in script
    assert 'attributes.family_name' in script
    assert 'attributes.email' in script
    assert "updateAttributes" in script
    assert 'Name: "given_name"' in script
    assert 'Name: "family_name"' in script
    assert "preferredProvider" in script


def test_signup_collects_and_writes_cognito_names():
    html = (ROOT / "frontend" / "signup.html").read_text()
    script = (ROOT / "frontend" / "signup.js").read_text()

    assert 'id="signupFirstName"' in html
    assert 'id="signupLastName"' in html
    assert 'Name: "given_name"' in script
    assert 'Name: "family_name"' in script
    assert "userPool.signUp(email, password, attributes" in script


def test_cognito_client_allows_name_attribute_access():
    terraform = (
        ROOT / "infra" / "modules" / "shared_foundation" / "main.tf"
    ).read_text()

    assert "read_attributes" in terraform
    assert "write_attributes" in terraform
    assert '"given_name"' in terraform
    assert '"family_name"' in terraform


def test_profile_cognito_operations_wait_for_a_valid_session():
    script = (ROOT / "frontend" / "profile.js").read_text()

    assert "async function getAuthenticatedCognitoUser()" in script
    assert "await getCurrentSession();" in script
    assert "const user = await getAuthenticatedCognitoUser();" in script
    assert script.count("const user = await getAuthenticatedCognitoUser();") == 2


def test_profile_asset_version_is_bumped_for_session_fix():
    html = (ROOT / "frontend" / "profile.html").read_text()

    assert './profile.js?v=4' in html
