from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_frontend_infrastructure_contract_exists():
    text = (ROOT / "infra" / "frontend.tf").read_text()

    required_blocks = (
        'resource "aws_s3_bucket" "frontend"',
        'resource "aws_cloudfront_origin_access_control" "frontend"',
        'resource "aws_cloudfront_distribution" "frontend"',
        'resource "aws_s3_bucket_policy" "frontend"',
        'resource "aws_acm_certificate" "frontend"',
        'resource "aws_route53_record" "frontend_a"',
        'resource "aws_route53_record" "frontend_aaaa"',
    )

    for block in required_blocks:
        assert block in text


def test_frontend_outputs_support_deployment():
    text = (ROOT / "infra" / "outputs.tf").read_text()

    for output_name in (
        "frontend_url",
        "frontend_bucket_name",
        "cloudfront_distribution_id",
        "cloudfront_distribution_domain_name",
        "primary_frontend_site",
        "cognito_user_pool_id",
        "cognito_user_pool_client_id",
    ):
        assert f'output "{output_name}"' in text


def test_frontend_deployment_script_uses_live_terraform_outputs():
    text = (ROOT / "tools" / "operations" / "deploy_frontend.sh").read_text()

    assert "output -json primary_frontend_site" in text
    assert "terraform_output_raw cognito_user_pool_id" in text
    assert "terraform_output_raw cognito_user_pool_client_id" in text
    assert "terraform_output_raw frontend_bucket_name" in text
    assert "terraform_output_raw cloudfront_distribution_id" in text
    assert 'aws s3 sync "$STAGING_DIR/"' in text
    assert 'cp -a "$FRONTEND_DIR/." "$STAGING_DIR/"' in text
    assert '"$STAGING_DIR/config.js"' in text
    assert '--cache-control "no-store, no-cache, must-revalidate, max-age=0"' in text
    assert "aws cloudfront create-invalidation" in text
    assert "aws cloudfront wait invalidation-completed" in text
    assert "aws s3api head-object" in text


def test_workflow_delegates_frontend_deployment_to_canonical_tool():
    text = (ROOT / ".github" / "workflows" / "terraform.yml").read_text()

    assert "Deploy frontend" in text
    assert "tools/operations/deploy_frontend.sh" in text
    assert "cat > frontend/config.js" not in text
    assert "aws s3 sync frontend/" not in text


def test_repository_frontend_config_template_contains_no_environment_specific_ids():
    text = (ROOT / "frontend" / "config.template.js").read_text()

    assert 'apiEndpoint: ""' in text
    assert 'cognitoUserPoolId: ""' in text
    assert 'cognitoUserPoolClientId: ""' in text
    assert "execute-api" not in text


def test_generated_frontend_config_is_ignored_by_git():
    text = (ROOT / ".gitignore").read_text()
    assert "frontend/config.js" in text


def test_auth_helper_does_not_hardcode_cognito_client_id():
    text = (ROOT / "tools" / "prepare" / "auth.sh").read_text()

    assert "terraform -chdir=" in text
    assert "output -raw cognito_user_pool_client_id" in text
    assert "6vhud9ve4t9acijtugqaf338mp" not in text


def test_frontend_origin_is_allowed_by_default_cors_configuration():
    text = (ROOT / "infra" / "variables.tf").read_text()
    assert '"https://resume.michaelpopovich.com"' in text
