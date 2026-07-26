mock_provider "aws" {
  alias = "us_east_1"
}

mock_provider "aws" {
  alias = "us_west_2"
}

run "production_observability_contract_is_explicit" {
  command = plan

  variables {
    enable_observability_dashboard = true
    enable_operational_alarms      = true
    enable_synthetic_monitoring    = true
    enable_global_api_routing      = true
    route53_public_zone_id         = "Z123456789"
    east_api_certificate_arn       = "arn:aws:acm:us-east-1:123456789012:certificate/11111111-1111-1111-1111-111111111111"
    west_api_certificate_arn       = "arn:aws:acm:us-west-2:123456789012:certificate/22222222-2222-2222-2222-222222222222"
  }

  assert {
    condition     = output.production_observability.enabled
    error_message = "MS-023 must expose the enabled production-observability contract."
  }

  assert {
    condition     = output.production_observability.mode == "DASHBOARD_ALARMS_AND_SYNTHETICS"
    error_message = "MS-023 must expose the selected observability mode."
  }

  assert {
    condition     = output.production_observability.cost_boundary.canary_count == 3
    error_message = "MS-023 must explicitly expose the three-canary cost boundary."
  }

  assert {
    condition     = contains(output.production_observability.alarm_categories, "LAMBDA_THROTTLES")
    error_message = "Lambda throttling must be represented in the alarm contract."
  }

  assert {
    condition     = length(output.observability.synthetics.canaries) == 3
    error_message = "Global, east, and west canaries must be represented."
  }
}
