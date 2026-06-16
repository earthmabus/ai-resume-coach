resource "aws_cognito_user_pool" "users" {
  name = "${local.name_prefix}-users"

  username_attributes = ["email"]

  auto_verified_attributes = ["email"]

  verification_message_template {
    default_email_option  = "CONFIRM_WITH_LINK"
    email_subject_by_link = "Verify your AI Resume Coach account"
    email_message_by_link = <<EOT
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

  tags = {
    Project     = "ai-resume-coach"
    Environment = "dev"
    ManagedBy   = "Terraform"
  }
}

resource "aws_cognito_user_pool_client" "web" {
  name         = "${local.name_prefix}-web-client"
  user_pool_id = aws_cognito_user_pool.users.id

  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  prevent_user_existence_errors = "ENABLED"
}
