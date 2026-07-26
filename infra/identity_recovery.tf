data "aws_caller_identity" "identity_recovery" {
  provider = aws.us_west_2
}

locals {
  cognito_recovery_domain_prefix = trimspace(var.cognito_recovery_domain_prefix) != "" ? trimspace(var.cognito_recovery_domain_prefix) : "${var.project_name}-${data.aws_caller_identity.identity_recovery.account_id}-recovery"
}

resource "aws_cognito_user_pool" "recovery" {
  provider = aws.us_west_2
  count    = var.enable_cognito_recovery ? 1 : 0

  name = "${var.project_name}-${var.environment}-usw2-recovery-users"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  verification_message_template {
    default_email_option  = "CONFIRM_WITH_LINK"
    email_subject_by_link = "Verify your AI Resume Coach recovery account"
    email_message_by_link = <<-EOT
      AI Resume Coach identity recovery is active.

      Please verify your email address by clicking the link below:

      {##Verify your email##}

      After verification, return to the AI Resume Coach login page and sign in.
    EOT
  }

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  tags = merge(
    local.common_tags,
    {
      Capability = "identity-recovery"
      RegionRole = "standby"
      Site       = "west"
      Scope      = "regional"
    },
  )
}

resource "aws_cognito_user_pool_client" "recovery_web" {
  provider = aws.us_west_2
  count    = var.enable_cognito_recovery ? 1 : 0

  name         = "${var.project_name}-${var.environment}-usw2-recovery-web-client"
  user_pool_id = aws_cognito_user_pool.recovery[0].id

  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  prevent_user_existence_errors = "ENABLED"

  read_attributes = [
    "email",
    "email_verified",
    "family_name",
    "given_name",
  ]

  write_attributes = [
    "family_name",
    "given_name",
  ]
}

resource "aws_cognito_user_pool_domain" "recovery" {
  provider = aws.us_west_2
  count    = var.enable_cognito_recovery ? 1 : 0

  domain       = local.cognito_recovery_domain_prefix
  user_pool_id = aws_cognito_user_pool.recovery[0].id
}
