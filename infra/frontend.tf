data "aws_route53_zone" "frontend" {
  provider = aws.us_east_1

  count        = var.enable_frontend_hosting ? 1 : 0
  name         = var.frontend_hosted_zone_name
  private_zone = false
}

resource "aws_s3_bucket" "frontend" {
  provider = aws.us_east_1

  count         = var.enable_frontend_hosting ? 1 : 0
  bucket        = "${local.global_name_prefix}-frontend-${data.aws_caller_identity.current.account_id}"
  force_destroy = var.frontend_bucket_force_destroy

  tags = merge(local.common_tags, {
    Name       = "${local.global_name_prefix}-frontend"
    Scope      = "global"
    RegionRole = "shared"
  })
}

resource "aws_s3_bucket_ownership_controls" "frontend" {
  provider = aws.us_east_1

  count  = var.enable_frontend_hosting ? 1 : 0
  bucket = aws_s3_bucket.frontend[0].id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  provider = aws.us_east_1

  count  = var.enable_frontend_hosting ? 1 : 0
  bucket = aws_s3_bucket.frontend[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  provider = aws.us_east_1

  count  = var.enable_frontend_hosting ? 1 : 0
  bucket = aws_s3_bucket.frontend[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_acm_certificate" "frontend" {
  provider = aws.us_east_1

  count             = var.enable_frontend_hosting ? 1 : 0
  domain_name       = var.frontend_domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name       = "${local.global_name_prefix}-frontend"
    Scope      = "global"
    RegionRole = "shared"
  })
}

resource "aws_route53_record" "frontend_certificate_validation" {
  provider = aws.us_east_1

  count = var.enable_frontend_hosting ? 1 : 0

  zone_id = data.aws_route53_zone.frontend[0].zone_id
  name    = tolist(aws_acm_certificate.frontend[0].domain_validation_options)[0].resource_record_name
  type    = tolist(aws_acm_certificate.frontend[0].domain_validation_options)[0].resource_record_type
  records = [tolist(aws_acm_certificate.frontend[0].domain_validation_options)[0].resource_record_value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "frontend" {
  provider = aws.us_east_1

  count                   = var.enable_frontend_hosting ? 1 : 0
  certificate_arn         = aws_acm_certificate.frontend[0].arn
  validation_record_fqdns = [aws_route53_record.frontend_certificate_validation[0].fqdn]
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  provider = aws.us_east_1

  count                             = var.enable_frontend_hosting ? 1 : 0
  name                              = "${local.global_name_prefix}-frontend"
  description                       = "Private S3 access for the AI Resume Coach frontend"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_cache_policy" "frontend" {
  provider = aws.us_east_1

  count       = var.enable_frontend_hosting ? 1 : 0
  name        = "${local.global_name_prefix}-frontend"
  default_ttl = var.frontend_cache_default_ttl_seconds
  max_ttl     = var.frontend_cache_max_ttl_seconds
  min_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true

    cookies_config {
      cookie_behavior = "none"
    }

    headers_config {
      header_behavior = "none"
    }

    query_strings_config {
      query_string_behavior = "none"
    }
  }
}

resource "aws_cloudfront_response_headers_policy" "frontend" {
  provider = aws.us_east_1

  count = var.enable_frontend_hosting ? 1 : 0
  name  = "${local.global_name_prefix}-frontend-security"

  security_headers_config {
    content_type_options {
      override = true
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }

    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      preload                    = true
      override                   = true
    }

    xss_protection {
      mode_block = true
      protection = true
      override   = true
    }
  }
}

resource "aws_cloudfront_distribution" "frontend" {
  provider = aws.us_east_1

  count               = var.enable_frontend_hosting ? 1 : 0
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "AI Resume Coach frontend"
  default_root_object = "index.html"
  aliases             = [var.frontend_domain_name]
  price_class         = var.frontend_cloudfront_price_class

  origin {
    domain_name              = aws_s3_bucket.frontend[0].bucket_regional_domain_name
    origin_id                = "frontend-s3"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend[0].id
  }

  default_cache_behavior {
    target_origin_id       = "frontend-s3"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    compress               = true

    cache_policy_id            = aws_cloudfront_cache_policy.frontend[0].id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend[0].id
  }

  custom_error_response {
    error_code            = 403
    response_code         = 404
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 404
    response_code         = 404
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.frontend[0].certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = merge(local.common_tags, {
    Name       = "${local.global_name_prefix}-frontend"
    Scope      = "global"
    RegionRole = "shared"
  })

  depends_on = [aws_acm_certificate_validation.frontend]
}

resource "aws_s3_bucket_policy" "frontend" {
  provider = aws.us_east_1

  count  = var.enable_frontend_hosting ? 1 : 0
  bucket = aws_s3_bucket.frontend[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontReadOnly"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.frontend[0].arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.frontend[0].arn
          }
        }
      }
    ]
  })
}

resource "aws_route53_record" "frontend_a" {
  provider = aws.us_east_1

  count   = var.enable_frontend_hosting ? 1 : 0
  zone_id = data.aws_route53_zone.frontend[0].zone_id
  name    = var.frontend_domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.frontend[0].domain_name
    zone_id                = aws_cloudfront_distribution.frontend[0].hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "frontend_aaaa" {
  provider = aws.us_east_1

  count   = var.enable_frontend_hosting ? 1 : 0
  zone_id = data.aws_route53_zone.frontend[0].zone_id
  name    = var.frontend_domain_name
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.frontend[0].domain_name
    zone_id                = aws_cloudfront_distribution.frontend[0].hosted_zone_id
    evaluate_target_health = false
  }
}
