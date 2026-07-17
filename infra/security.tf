locals {
  cognito_waf_name = "${local.global_name_prefix}-cognito-waf"

  cognito_waf_managed_rule_groups = [
    "AWSManagedRulesCommonRuleSet",
    "AWSManagedRulesKnownBadInputsRuleSet",
    "AWSManagedRulesAmazonIpReputationList",
  ]
}

resource "aws_wafv2_web_acl" "cognito" {
  count    = var.enable_cognito_waf ? 1 : 0
  provider = aws.us_east_1

  name        = local.cognito_waf_name
  description = "Cost-gated baseline protection for the shared Cognito user pool."
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 10

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.cognito_waf_name}-common"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 20

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.cognito_waf_name}-known-bad-inputs"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesAmazonIpReputationList"
    priority = 30

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.cognito_waf_name}-ip-reputation"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "PerIpRateLimit"
    priority = 40

    action {
      block {}
    }

    statement {
      rate_based_statement {
        aggregate_key_type = "IP"
        limit              = var.cognito_waf_rate_limit
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.cognito_waf_name}-rate-limit"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = local.cognito_waf_name
    sampled_requests_enabled   = true
  }

  tags = merge(
    local.common_tags,
    {
      Scope      = "global"
      RegionRole = "shared"
      Capability = "identity-edge-protection"
    },
  )
}

resource "aws_wafv2_web_acl_association" "cognito" {
  count    = var.enable_cognito_waf ? 1 : 0
  provider = aws.us_east_1

  resource_arn = aws_cognito_user_pool.users.arn
  web_acl_arn  = aws_wafv2_web_acl.cognito[0].arn
}

resource "aws_cloudwatch_log_group" "cognito_waf" {
  count    = var.enable_cognito_waf && var.enable_cognito_waf_logging ? 1 : 0
  provider = aws.us_east_1

  name              = "aws-waf-logs-${local.global_name_prefix}-cognito"
  retention_in_days = var.cognito_waf_log_retention_days

  tags = merge(
    local.common_tags,
    {
      Scope      = "global"
      RegionRole = "shared"
      Capability = "security-logs"
    },
  )
}

resource "aws_wafv2_web_acl_logging_configuration" "cognito" {
  count    = var.enable_cognito_waf && var.enable_cognito_waf_logging ? 1 : 0
  provider = aws.us_east_1

  log_destination_configs = [
    aws_cloudwatch_log_group.cognito_waf[0].arn,
  ]

  resource_arn = aws_wafv2_web_acl.cognito[0].arn

  redacted_fields {
    single_header {
      name = "authorization"
    }
  }

  logging_filter {
    default_behavior = "DROP"

    filter {
      behavior    = "KEEP"
      requirement = "MEETS_ANY"

      condition {
        action_condition {
          action = "BLOCK"
        }
      }

      condition {
        action_condition {
          action = "COUNT"
        }
      }
    }
  }
}
