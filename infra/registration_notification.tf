data "aws_caller_identity" "current" {
  provider = aws.us_east_1
}

resource "aws_sns_topic" "user_registration_notifications" {
  provider = aws.us_east_1

  name = "${local.global_name_prefix}-user-registration-notifications"

  tags = merge(
    local.common_tags,
    {
      Scope      = "global"
      RegionRole = "shared"
      Capability = "registration-notification"
    },
  )
}

resource "aws_sns_topic_subscription" "user_registration_email" {
  provider = aws.us_east_1
  count    = trimspace(var.registration_notification_email) != "" ? 1 : 0

  topic_arn = aws_sns_topic.user_registration_notifications.arn
  protocol  = "email"
  endpoint  = trimspace(var.registration_notification_email)
}

resource "aws_cloudwatch_log_group" "registration_notification" {
  provider = aws.us_east_1

  name              = "/aws/lambda/${local.global_name_prefix}-registration-notification"
  retention_in_days = 14

  tags = merge(
    local.common_tags,
    {
      Scope      = "global"
      RegionRole = "shared"
      Capability = "registration-notification"
    },
  )
}

resource "aws_iam_role" "registration_notification" {
  provider = aws.us_east_1

  name = "${local.global_name_prefix}-registration-notification-role"

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
    local.common_tags,
    {
      Scope      = "global"
      RegionRole = "shared"
      Capability = "registration-notification"
    },
  )
}

resource "aws_iam_role_policy_attachment" "registration_notification_logging" {
  provider = aws.us_east_1

  role       = aws_iam_role.registration_notification.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "registration_notification_publish" {
  provider = aws.us_east_1

  name = "${local.global_name_prefix}-registration-notification-publish"
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
  provider = aws.us_east_1

  function_name = "${local.global_name_prefix}-registration-notification"
  role          = aws_iam_role.registration_notification.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.13"

  filename         = data.archive_file.registration_notification_zip.output_path
  source_code_hash = data.archive_file.registration_notification_zip.output_base64sha256

  timeout     = 10
  memory_size = 128

  environment {
    variables = {
      PROJECT_NAME                        = var.project_name
      ENVIRONMENT                         = var.environment
      APP_VERSION                         = var.app_version
      DEPLOYMENT_ID                       = var.deployment_id
      LOG_LEVEL                           = upper(var.log_level)
      REGISTRATION_NOTIFICATION_TOPIC_ARN = aws_sns_topic.user_registration_notifications.arn
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.registration_notification,
    aws_iam_role_policy_attachment.registration_notification_logging,
    aws_iam_role_policy.registration_notification_publish,
  ]

  tags = merge(
    local.common_tags,
    {
      Scope      = "global"
      RegionRole = "shared"
      Capability = "registration-notification"
    },
  )
}

resource "aws_lambda_permission" "allow_cognito_registration_notification" {
  provider = aws.us_east_1

  statement_id  = "AllowCognitoRegistrationNotification"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.registration_notification.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.users.arn
}
