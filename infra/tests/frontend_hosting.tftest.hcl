mock_provider "aws" {
  alias = "us_east_1"
}

mock_provider "aws" {
  alias = "us_west_2"
}

mock_provider "aws" {
  alias = "us_east_2"
}

run "frontend_hosting_contract" {
  command = plan

  variables {
    enable_frontend_hosting   = true
    frontend_domain_name      = "resume.example.com"
    frontend_hosted_zone_name = "example.com"
  }

  assert {
    condition     = length(aws_s3_bucket.frontend) == 1
    error_message = "Frontend hosting must create exactly one private S3 bucket."
  }

  assert {
    condition     = length(aws_cloudfront_distribution.frontend) == 1
    error_message = "Frontend hosting must create exactly one CloudFront distribution."
  }

  assert {
    condition     = aws_cloudfront_distribution.frontend[0].default_root_object == "index.html"
    error_message = "CloudFront must use index.html as the default root object."
  }

  assert {
    condition     = contains(aws_cloudfront_distribution.frontend[0].aliases, "resume.example.com")
    error_message = "CloudFront must publish the configured frontend alias."
  }

  assert {
    condition     = length(aws_route53_record.frontend_a) == 1 && length(aws_route53_record.frontend_aaaa) == 1
    error_message = "Frontend hosting must create IPv4 and IPv6 Route 53 aliases."
  }
}
