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

run "both_sites_are_routable_by_default" {
  command = plan

  assert {
    condition = (
      output.operations.routing_enabled_by_site.east
      && output.operations.routing_enabled_by_site.west
      && length(output.operations.active_sites) == 2
    )
    error_message = "Both active sites must be routable by default."
  }
}

run "east_can_be_isolated_while_west_remains_active" {
  command = plan

  variables {
    site_routing_enabled = {
      east = false
      west = true
    }
  }

  assert {
    condition = (
      output.operations.routing_enabled_by_site.east == false
      && output.operations.routing_enabled_by_site.west
      && toset(output.operations.active_sites) == toset(["west"])
    )
    error_message = "East must be independently removable from global routing."
  }
}

run "west_can_be_isolated_while_east_remains_active" {
  command = plan

  variables {
    site_routing_enabled = {
      east = true
      west = false
    }
  }

  assert {
    condition = (
      output.operations.routing_enabled_by_site.east
      && output.operations.routing_enabled_by_site.west == false
      && toset(output.operations.active_sites) == toset(["east"])
    )
    error_message = "West must be independently removable from global routing."
  }
}

run "disabling_both_sites_is_rejected" {
  command = plan

  variables {
    site_routing_enabled = {
      east = false
      west = false
    }
  }

  expect_failures = [var.site_routing_enabled]
}

run "production_readiness_reports_missing_controls_without_enforcement" {
  command = plan

  assert {
    condition = (
      output.operations.production_readiness_enforced == false
      && output.operations.production_ready == false
      && length(output.operations.missing_production_controls) == 6
      && contains(output.operations.missing_production_controls, "global_api_routing")
      && contains(output.operations.missing_production_controls, "synthetic_monitoring")
    )
    error_message = "Readiness must remain informative without blocking cost-gated development plans."
  }
}

run "deployment_and_rollback_contracts_are_explicit" {
  command = plan

  assert {
    condition = (
      output.operations.deployment.strategy == "REGIONAL_SEQUENTIAL"
      && output.operations.deployment.order[0] == "west"
      && output.operations.deployment.order[4] == "enable-global-routing"
      && output.operations.rollback.unit == "REGIONAL_SITE"
      && output.operations.rollback.routing == "disable-affected-site-route53-record"
    )
    error_message = "The platform must expose the approved sequential deployment and regional rollback contract."
  }
}

run "production_readiness_succeeds_when_required_controls_are_enabled" {
  command = plan

  variables {
    production_readiness_enforced    = true
    enable_global_api_routing        = true
    enable_route53_api_health_checks = true
    enable_cognito_waf               = true
    enable_observability_dashboard   = true
    enable_operational_alarms        = true
    enable_synthetic_monitoring      = true

    api_domain_name        = "api.resume.example.com"
    route53_public_zone_id = "Z0123456789EXAMPLE"

    east_api_certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/11111111-1111-1111-1111-111111111111"
    west_api_certificate_arn = "arn:aws:acm:us-west-2:123456789012:certificate/22222222-2222-2222-2222-222222222222"
  }

  assert {
    condition = (
      output.operations.production_readiness_enforced
      && output.operations.production_ready
      && length(output.operations.missing_production_controls) == 0
      && length(output.operations.active_sites) == 2
    )
    error_message = "Production readiness must pass when every required control is enabled."
  }
}
