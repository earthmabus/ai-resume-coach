data "aws_caller_identity" "current" {}

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  shared_tags = merge(
    var.common_tags,
    {
      Scope      = "global"
      RegionRole = "shared"
    },
  )
}

resource "aws_sns_topic" "user_registration_notifications" {
  name = "${local.name_prefix}-user-registration-notifications"

  tags = merge(
    local.shared_tags,
    {
      Capability = "registration-notification"
    },
  )
}

resource "aws_sns_topic_subscription" "user_registration_email" {
  count = trimspace(var.registration_notification_email) != "" ? 1 : 0

  topic_arn = aws_sns_topic.user_registration_notifications.arn
  protocol  = "email"
  endpoint  = trimspace(var.registration_notification_email)
}

resource "aws_cloudwatch_log_group" "registration_notification" {
  name              = "/aws/lambda/${local.name_prefix}-registration-notification"
  retention_in_days = 14

  tags = merge(
    local.shared_tags,
    {
      Capability = "registration-notification"
    },
  )
}

resource "aws_iam_role" "registration_notification" {
  name = "${local.name_prefix}-registration-notification-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Principal = {
          Service = "lambda.amazonaws.com"
        }

        Action = "sts:AssumeRole"
      },
    ]
  })

  tags = merge(
    local.shared_tags,
    {
      Capability = "registration-notification"
    },
  )
}

resource "aws_iam_role_policy_attachment" "registration_notification_logging" {
  role       = aws_iam_role.registration_notification.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "registration_notification_publish" {
  name = "${local.name_prefix}-registration-notification-publish"
  role = aws_iam_role.registration_notification.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid      = "PublishRegistrationNotification"
        Effect   = "Allow"
        Action   = "sns:Publish"
        Resource = aws_sns_topic.user_registration_notifications.arn
      },
    ]
  })
}

resource "aws_lambda_function" "registration_notification" {
  function_name = "${local.name_prefix}-registration-notification"
  role          = aws_iam_role.registration_notification.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.13"

  filename         = var.registration_notification_package.filename
  source_code_hash = var.registration_notification_package.source_code_hash

  timeout     = 10
  memory_size = 128

  environment {
    variables = {
      PROJECT_NAME                        = var.project_name
      ENVIRONMENT                         = var.environment
      APP_VERSION                         = var.runtime.app_version
      DEPLOYMENT_ID                       = var.runtime.deployment_id
      LOG_LEVEL                           = upper(var.runtime.log_level)
      REGISTRATION_NOTIFICATION_TOPIC_ARN = aws_sns_topic.user_registration_notifications.arn
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.registration_notification,
    aws_iam_role_policy_attachment.registration_notification_logging,
    aws_iam_role_policy.registration_notification_publish,
  ]

  tags = merge(
    local.shared_tags,
    {
      Capability = "registration-notification"
    },
  )
}

resource "aws_cognito_user_pool" "users" {
  name = "${local.name_prefix}-users"

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
    local.shared_tags,
    {
      Capability = "identity"
    },
  )
}

resource "aws_cognito_user_pool_client" "web" {
  name         = "${local.name_prefix}-web-client"
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
  count = var.enable_synthetic_placement_override ? 1 : 0

  name         = var.synthetic_placement_override_group_name
  user_pool_id = aws_cognito_user_pool.users.id
  description  = "Development-only group allowed to request synthetic owner-region placement."
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.project_name}-${data.aws_caller_identity.current.account_id}"
  user_pool_id = aws_cognito_user_pool.users.id
}

resource "aws_lambda_permission" "allow_cognito_registration_notification" {
  statement_id  = "AllowCognitoRegistrationNotification"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.registration_notification.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.users.arn
}

resource "aws_dynamodb_table" "resume_analysis" {
  name         = "${local.name_prefix}-resume-analysis"
  billing_mode = "PAY_PER_REQUEST"
  table_class  = "STANDARD"

  deletion_protection_enabled = var.dynamodb_deletion_protection_enabled

  # The AWS provider currently supports key_schema for GSIs, but the
  # table-level schema remains hash_key/range_key in provider v6.55.0.
  hash_key  = "pk"
  range_key = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "gsi1pk"
    type = "S"
  }

  attribute {
    name = "gsi1sk"
    type = "S"
  }

  attribute {
    name = "gsi2pk"
    type = "S"
  }

  attribute {
    name = "gsi2sk"
    type = "S"
  }

  global_secondary_index {
    name = "gsi1"

    key_schema {
      attribute_name = "gsi1pk"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "gsi1sk"
      key_type       = "RANGE"
    }

    projection_type = "ALL"
  }

  global_secondary_index {
    name = "gsi2"

    key_schema {
      attribute_name = "gsi2pk"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "gsi2sk"
      key_type       = "RANGE"
    }

    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled                 = true
    recovery_period_in_days = var.dynamodb_pitr_recovery_period_days
  }

  server_side_encryption {
    enabled = true
  }

  replica {
    region_name            = var.west_region
    consistency_mode       = "STRONG"
    point_in_time_recovery = true
    propagate_tags         = true
  }

  global_table_witness {
    region_name = var.witness_region
  }

  tags = merge(
    var.common_tags,
    {
      Scope          = "multi-region-data"
      Capability     = "resume-analysis-system-of-record"
      Consistency    = "multi-region-strong"
      PrimaryReplica = var.east_region
      PeerReplica    = var.west_region
      WitnessRegion  = var.witness_region
    },
  )
}
