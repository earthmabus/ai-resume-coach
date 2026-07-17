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

run "edge_security_is_cost_gated_by_default" {
  command = plan

  assert {
    condition = (
      output.edge_security.cognito_waf.enabled == false
      &&
      output.edge_security.cognito_waf.logging_enabled == false
    )
    error_message = "Cognito WAF and WAF logging must be disabled by default."
  }

  assert {
    condition = (
      output.edge_security.cognito_waf.scope == "REGIONAL"
      &&
      output.edge_security.cognito_waf.protected_resource == "COGNITO_USER_POOL"
    )
    error_message = "The WAF contract must target the shared Cognito user pool."
  }

  assert {
    condition = (
      output.edge_security.ddos_baseline == "AWS_SHIELD_STANDARD"
      &&
      output.edge_security.regional_http_apis.waf_association_supported == false
    )
    error_message = "The security contract must document Shield Standard and the HTTP API WAF limitation."
  }
}

run "cognito_waf_uses_baseline_managed_protections" {
  command = plan

  variables {
    enable_cognito_waf         = true
    enable_cognito_waf_logging = false
    cognito_waf_rate_limit     = 750
  }

  assert {
    condition     = output.edge_security.cognito_waf.enabled
    error_message = "Cognito WAF must be enabled when explicitly requested."
  }

  assert {
    condition = (
      output.edge_security.cognito_waf.rate_limit == 750
      &&
      length(output.edge_security.cognito_waf.managed_rule_groups) == 3
      &&
      contains(
        output.edge_security.cognito_waf.managed_rule_groups,
        "AWSManagedRulesCommonRuleSet",
      )
      &&
      contains(
        output.edge_security.cognito_waf.managed_rule_groups,
        "AWSManagedRulesKnownBadInputsRuleSet",
      )
      &&
      contains(
        output.edge_security.cognito_waf.managed_rule_groups,
        "AWSManagedRulesAmazonIpReputationList",
      )
    )
    error_message = "Cognito WAF must use the approved managed-rule baseline and configured rate limit."
  }
}

run "waf_logging_is_explicit_and_privacy_aware" {
  command = plan

  variables {
    enable_cognito_waf             = true
    enable_cognito_waf_logging     = true
    cognito_waf_log_retention_days = 7
  }

  assert {
    condition = (
      output.edge_security.cognito_waf.enabled
      &&
      output.edge_security.cognito_waf.logging_enabled
      &&
      output.edge_security.cognito_waf.log_retention_days == 7
    )
    error_message = "WAF logging must be explicitly enabled with short retention."
  }

  assert {
    condition = (
      length(output.edge_security.cognito_waf.redacted_headers) == 1
      &&
      contains(
        output.edge_security.cognito_waf.redacted_headers,
        "authorization",
      )
    )
    error_message = "WAF logging must redact the Authorization header."
  }
}

run "regional_http_apis_retain_throttling_controls" {
  command = plan

  assert {
    condition = (
      output.edge_security.regional_http_apis.protection_model
      == "JWT_AUTHORIZATION_PLUS_STAGE_THROTTLING"
      &&
      output.edge_security.regional_http_apis.east_throttling.burst_limit > 0
      &&
      output.edge_security.regional_http_apis.east_throttling.rate_limit > 0
      &&
      output.edge_security.regional_http_apis.west_throttling.burst_limit > 0
      &&
      output.edge_security.regional_http_apis.west_throttling.rate_limit > 0
    )
    error_message = "Both Regional HTTP APIs must retain positive stage throttling limits."
  }

  assert {
    condition = (
      output.edge_security.regional_http_apis.east_throttling
      ==
      output.edge_security.regional_http_apis.west_throttling
    )
    error_message = "Regional API throttling contracts must remain symmetric."
  }
}
