data "archive_file" "outbox_publisher_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/outbox_publisher.zip"
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

resource "aws_iam_role_policy" "outbox_publisher_sqs" {
  name = "${local.name_prefix}-outbox-publisher-sqs"
  role = aws_iam_role.outbox_publisher.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.resume_analysis_jobs.arn
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

  environment {
    variables = {
      PROJECT_NAME  = var.project_name
      ENVIRONMENT   = var.environment
      APP_VERSION   = var.app_version
      DEPLOYMENT_ID = var.deployment_id
      LOG_LEVEL     = var.log_level

      RESUME_ANALYSIS_TABLE              = aws_dynamodb_table.resume_analysis.name
      RESUME_ANALYSIS_QUEUE_URL          = aws_sqs_queue.resume_analysis_jobs.url
      OUTBOX_BATCH_SIZE                  = "25"
      OUTBOX_MAX_WORKERS                 = "4"
      OUTBOX_MAX_DELIVERY_ATTEMPTS       = "20"
      OUTBOX_DELIVERED_RETENTION_SECONDS = "2592000"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.outbox_publisher,
    aws_iam_role_policy_attachment.outbox_publisher_logging,
    aws_iam_role_policy.outbox_publisher_dynamodb,
    aws_iam_role_policy.outbox_publisher_sqs,
  ]
}

resource "aws_cloudwatch_event_rule" "outbox_publisher_schedule" {
  name                = "${local.name_prefix}-outbox-publisher-schedule"
  description         = "Invokes the transactional outbox publisher once per minute."
  schedule_expression = "rate(1 minute)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "outbox_publisher" {
  rule      = aws_cloudwatch_event_rule.outbox_publisher_schedule.name
  target_id = "OutboxPublisherLambda"
  arn       = aws_lambda_function.outbox_publisher.arn

  input = jsonencode({
    source = "scheduled-outbox-publisher"
  })
}

resource "aws_lambda_permission" "allow_outbox_publisher_schedule" {
  statement_id  = "AllowOutboxPublisherSchedule"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.outbox_publisher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.outbox_publisher_schedule.arn
}
