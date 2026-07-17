locals {
  global_api_sites = var.global_api.enabled ? {
    east = {
      region          = var.primary_site.region
      region_code     = var.primary_site.region_code
      api_id          = var.primary_site.api_id
      certificate_arn = var.global_api.east_certificate_arn
    }
    west = {
      region          = var.secondary_site.region
      region_code     = var.secondary_site.region_code
      api_id          = var.secondary_site.api_id
      certificate_arn = var.global_api.west_certificate_arn
    }
  } : {}

  route53_health_check_regions = [
    "us-east-1",
    "us-west-1",
    "us-west-2",
  ]
}

resource "aws_apigatewayv2_domain_name" "east" {
  count    = var.global_api.enabled ? 1 : 0
  provider = aws.us_east_1

  domain_name = var.global_api.domain_name

  domain_name_configuration {
    certificate_arn = var.global_api.east_certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  tags = merge(local.tags, {
    Capability = "global-api-routing"
    Site       = "east"
  })
}

resource "aws_apigatewayv2_domain_name" "west" {
  count    = var.global_api.enabled ? 1 : 0
  provider = aws.us_west_2

  domain_name = var.global_api.domain_name

  domain_name_configuration {
    certificate_arn = var.global_api.west_certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  tags = merge(local.tags, {
    Capability = "global-api-routing"
    Site       = "west"
  })
}

resource "aws_apigatewayv2_api_mapping" "east" {
  count    = var.global_api.enabled ? 1 : 0
  provider = aws.us_east_1

  api_id      = var.primary_site.api_id
  domain_name = aws_apigatewayv2_domain_name.east[0].id
  stage       = "$default"
}

resource "aws_apigatewayv2_api_mapping" "west" {
  count    = var.global_api.enabled ? 1 : 0
  provider = aws.us_west_2

  api_id      = var.secondary_site.api_id
  domain_name = aws_apigatewayv2_domain_name.west[0].id
  stage       = "$default"
}

resource "aws_route53_health_check" "east" {
  count = var.global_api.enabled && var.global_api.health_checks_enabled ? 1 : 0

  fqdn              = var.global_api.domain_name
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health/ready"
  request_interval  = 30
  failure_threshold = var.global_api.health_failure_threshold
  measure_latency   = false
  regions           = local.route53_health_check_regions

  tags = merge(local.tags, {
    Name       = "${local.name_prefix}-east-api-health"
    Capability = "dns-health-check"
    Site       = "east"
  })
}

resource "aws_route53_health_check" "west" {
  count = var.global_api.enabled && var.global_api.health_checks_enabled ? 1 : 0

  fqdn              = var.global_api.domain_name
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health/ready"
  request_interval  = 30
  failure_threshold = var.global_api.health_failure_threshold
  measure_latency   = false
  regions           = local.route53_health_check_regions

  tags = merge(local.tags, {
    Name       = "${local.name_prefix}-west-api-health"
    Capability = "dns-health-check"
    Site       = "west"
  })
}

resource "aws_route53_record" "east_api_a" {
  count = var.global_api.enabled && var.global_api.routing_enabled.east ? 1 : 0

  zone_id = var.global_api.hosted_zone_id
  name    = var.global_api.domain_name
  type    = "A"

  set_identifier = "${local.name_prefix}-east"

  latency_routing_policy {
    region = var.primary_site.region
  }

  health_check_id = var.global_api.health_checks_enabled ? aws_route53_health_check.east[0].id : null

  alias {
    name                   = aws_apigatewayv2_domain_name.east[0].domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.east[0].domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "west_api_a" {
  count = var.global_api.enabled && var.global_api.routing_enabled.west ? 1 : 0

  zone_id = var.global_api.hosted_zone_id
  name    = var.global_api.domain_name
  type    = "A"

  set_identifier = "${local.name_prefix}-west"

  latency_routing_policy {
    region = var.secondary_site.region
  }

  health_check_id = var.global_api.health_checks_enabled ? aws_route53_health_check.west[0].id : null

  alias {
    name                   = aws_apigatewayv2_domain_name.west[0].domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.west[0].domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}
