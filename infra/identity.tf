resource "aws_cognito_user_pool" "users" {
  provider = aws.us_east_1

  name = "${local.global_name_prefix}-users"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  lambda_config {
    post_confirmation = aws_lambda_function.registration_notification.arn
  }

  verification_message_template {
    default_email_option  = "CONFIRM_WITH_LINK"
    email_subject_by_link = "Verify your AI Resume Coach account"
    email_message_by_link = <<-EOT
      Welcome to AI Resume Coach!

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
      Scope      = "global"
      RegionRole = "shared"
      Capability = "identity"
    },
  )
}

resource "aws_cognito_user_pool_client" "web" {
  provider = aws.us_east_1

  name         = "${local.global_name_prefix}-web-client"
  user_pool_id = aws_cognito_user_pool.users.id

  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  prevent_user_existence_errors = "ENABLED"
}

resource "aws_cognito_user_group" "synthetic_runtime_validation" {
  provider = aws.us_east_1
  count    = var.enable_synthetic_placement_override ? 1 : 0

  name         = var.synthetic_placement_override_group_name
  user_pool_id = aws_cognito_user_pool.users.id
  description  = "Development-only group allowed to request synthetic owner-region placement."
}

resource "aws_cognito_user_pool_domain" "main" {
  provider = aws.us_east_1

  domain       = "${var.project_name}-${data.aws_caller_identity.current.account_id}"
  user_pool_id = aws_cognito_user_pool.users.id
}
