mock_provider "aws" {
  alias = "us_east_1"
}

mock_provider "aws" {
  alias = "us_west_2"
}

mock_provider "aws" {
  alias = "us_east_2"
}

mock_provider "archive" {}

run "global_api_routing_is_cost_gated_by_default" {
  command = plan

  assert {
    condition = (
      output.global_api_routing.enabled == false
      &&
      output.global_api_routing.health_checks_enabled == false
    )
    error_message = "Global API routing and paid Route 53 health checks must be disabled by default."
  }

  assert {
    condition = (
      output.global_api_routing.routing_policy == "LATENCY"
      &&
      output.global_api_routing.health_path == "/health/ready"
      &&
      output.global_api_routing.tls_policy == "TLS_1_2"
    )
    error_message = "The default global API routing contract is incorrect."
  }

  assert {
    condition = (
      length(output.global_api_routing.active_regions) == 2
      &&
      contains(output.global_api_routing.active_regions, "us-east-1")
      &&
      contains(output.global_api_routing.active_regions, "us-west-2")
    )
    error_message = "The global API routing contract must identify both active Regions."
  }
}

run "global_api_routing_composes_two_active_regions" {
  command = plan

  variables {
    enable_global_api_routing        = true
    enable_route53_api_health_checks = false

    api_domain_name        = "api.resume.example.com"
    route53_public_zone_id = "Z0123456789EXAMPLE"

    east_api_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/11111111-1111-1111-1111-111111111111"
    west_api_certificate_arn = "arn:aws:acm:us-west-2:123456789012:certificate/22222222-2222-2222-2222-222222222222"
  }

  assert {
    condition = (
      output.global_api_routing.enabled
      &&
      output.global_api_routing.health_checks_enabled == false
    )
    error_message = "Global API routing should be enabled without requiring paid Route 53 health checks."
  }

  assert {
    condition     = output.global_api_routing.domain_name == "api.resume.example.com"
    error_message = "The global API routing contract must expose the configured API hostname."
  }

  assert {
    condition = (
      length(output.global_api_routing.active_regions) == 2
      &&
      contains(output.global_api_routing.active_regions, "us-east-1")
      &&
      contains(output.global_api_routing.active_regions, "us-west-2")
    )
    error_message = "Global API routing must compose both active Regions."
  }

  assert {
    condition = (
      output.global_api_routing.routing_policy == "LATENCY"
      &&
      output.global_api_routing.health_path == "/health/ready"
      &&
      output.global_api_routing.tls_policy == "TLS_1_2"
    )
    error_message = "The global API routing policy, health path, or TLS policy is incorrect."
  }
}

run "route53_health_checks_can_be_enabled_explicitly" {
  command = plan

  variables {
    enable_global_api_routing        = true
    enable_route53_api_health_checks = true

    api_domain_name        = "api.resume.example.com"
    route53_public_zone_id = "Z0123456789EXAMPLE"

    east_api_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/11111111-1111-1111-1111-111111111111"
    west_api_certificate_arn = "arn:aws:acm:us-west-2:123456789012:certificate/22222222-2222-2222-2222-222222222222"
  }

  assert {
    condition = (
      output.global_api_routing.enabled
      &&
      output.global_api_routing.health_checks_enabled
    )
    error_message = "Route 53 health checks must be enabled only when explicitly requested."
  }

  assert {
    condition     = output.global_api_routing.health_path == "/health/ready"
    error_message = "Route 53 health checks must use the readiness endpoint."
  }
}
