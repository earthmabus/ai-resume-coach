data "archive_file" "registration_notification_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/registration_notification"
  output_path = "${path.module}/registration_notification.zip"
}

resource "aws_iam_role" "registration_notification_lambda_role" {
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
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "registration_notification_basic_execution" {
  role       = aws_iam_role.registration_notification_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "registration_notification_publish" {
  name = "${local.name_prefix}-registration-notification-publish"
  role = aws_iam_role.registration_notification_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "sns:Publish"
        Resource = aws_sns_topic.user_registration_notifications.arn
      }
    ]
  })
}

resource "aws_lambda_function" "registration_notification" {
  function_name = "${local.name_prefix}-registration-notification"
  role          = aws_iam_role.registration_notification_lambda_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.13"

  filename         = data.archive_file.registration_notification_zip.output_path
  source_code_hash = data.archive_file.registration_notification_zip.output_base64sha256

  timeout     = 10
  memory_size = 128

  environment {
    variables = {
      REGISTRATION_NOTIFICATION_TOPIC_ARN = aws_sns_topic.user_registration_notifications.arn
    }
  }
}

resource "aws_lambda_permission" "allow_cognito_registration_notification" {
  statement_id  = "AllowCognitoRegistrationNotification"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.registration_notification.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.users.arn
}
