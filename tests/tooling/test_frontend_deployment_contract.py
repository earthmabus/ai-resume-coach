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
    ):
        assert f'output "{output_name}"' in text


def test_workflow_generates_and_deploys_frontend():
    text = (ROOT / ".github" / "workflows" / "terraform.yml").read_text()

    assert "Generate frontend runtime configuration" in text
    assert "frontend/config.js" in text
    assert "aws s3 sync frontend/" in text
    assert "aws cloudfront create-invalidation" in text
    assert "terraform -chdir=infra output -raw frontend_url" in text


def test_frontend_origin_is_allowed_by_default_cors_configuration():
    text = (ROOT / "infra" / "variables.tf").read_text()
    assert '"https://resume.michaelpopovich.com"' in text
