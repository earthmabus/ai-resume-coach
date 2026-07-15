data "archive_file" "outbox_publisher_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/outbox_publisher.zip"
}

# Custom EventBridge bus for application domain events.
#
# The scheduled rule below runs on the account's default EventBridge bus.
# The publisher Lambda sends domain events to this custom bus.
resource "aws_cloudwatch_event_bus" "application" {
  name = "${local.name_prefix}-application-events"
}

resource "aws_iam_role" "outbox_publisher" {
  name = "${local.name_prefix}-outbox-publisher-role"

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

resource "aws_iam_role_policy_attachment" "outbox_publisher_logging" {
  role       = aws_iam_role.outbox_publisher.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "outbox_publisher_dynamodb" {
  name = "${local.name_prefix}-outbox-publisher-dynamodb"
  role = aws_iam_role.outbox_publisher.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Action = [
          "dynamodb:Query",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]

        Resource = [
          aws_dynamodb_table.resume_analysis.arn,
          "${aws_dynamodb_table.resume_analysis.arn}/index/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "outbox_publisher_eventbridge" {
  name = "${local.name_prefix}-outbox-publisher-eventbridge"
  role = aws_iam_role.outbox_publisher.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Action = [
          "events:PutEvents"
        ]

        Resource = aws_cloudwatch_event_bus.application.arn
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "outbox_publisher" {
  name              = "/aws/lambda/${local.name_prefix}-outbox-publisher"
  retention_in_days = 14
}

resource "aws_lambda_function" "outbox_publisher" {
  function_name = "${local.name_prefix}-outbox-publisher"
  role          = aws_iam_role.outbox_publisher.arn
  handler       = "outbox_publisher_handler.handler"
  runtime       = "python3.13"

  filename         = data.archive_file.outbox_publisher_zip.output_path
  source_code_hash = data.archive_file.outbox_publisher_zip.output_base64sha256

  timeout     = 30
  memory_size = 256

  # Operational protection against overlapping scheduled runs.
  # Conditional DynamoDB updates remain the authoritative
  # idempotency and concurrency protection.
  reserved_concurrent_executions = 1

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.resume_analysis.name
      EVENT_BUS_NAME      = aws_cloudwatch_event_bus.application.name
      OUTBOX_BATCH_SIZE   = "25"
      DEPLOYMENT_ID       = var.deployment_id
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.outbox_publisher,
    aws_iam_role_policy_attachment.outbox_publisher_logging,
    aws_iam_role_policy.outbox_publisher_dynamodb,
    aws_iam_role_policy.outbox_publisher_eventbridge,
  ]
}

# Scheduled rules run on the account's default EventBridge bus.
resource "aws_cloudwatch_event_rule" "outbox_publisher_schedule" {
  name                = "${local.name_prefix}-outbox-publisher-schedule"
  description         = "Runs the transactional outbox publisher."
  schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_target" "outbox_publisher" {
  rule      = aws_cloudwatch_event_rule.outbox_publisher_schedule.name
  target_id = "OutboxPublisherLambda"
  arn       = aws_lambda_function.outbox_publisher.arn

  input = jsonencode({
    source = "scheduled-outbox-publisher"
  })
}

resource "aws_lambda_permission" "allow_outbox_schedule" {
  statement_id  = "AllowOutboxPublisherSchedule"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.outbox_publisher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.outbox_publisher_schedule.arn
}
