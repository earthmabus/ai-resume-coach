locals {
  alarm_prefix = "${local.name_prefix}-observability"

  lambda_functions = {
    api              = aws_lambda_function.api.function_name
    worker           = aws_lambda_function.worker.function_name
    outbox_publisher = aws_lambda_function.outbox_publisher.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "api_5xx" {
  count = var.observability.operational_alarms_enabled ? 1 : 0

  alarm_name          = "${local.alarm_prefix}-api-5xx"
  alarm_description   = "Regional HTTP API 5XX responses exceeded the approved threshold."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = var.observability.api_5xx_threshold
  treat_missing_data  = "notBreaching"

  namespace   = "AWS/ApiGateway"
  metric_name = "5xx"
  statistic   = "Sum"
  period      = 60

  dimensions = {
    ApiId = aws_apigatewayv2_api.regional.id
    Stage = aws_apigatewayv2_stage.default.name
  }

  actions_enabled = length(var.observability.alarm_actions) > 0
  alarm_actions   = var.observability.alarm_actions
  ok_actions      = var.observability.alarm_actions

  tags = merge(local.tags, { Capability = "api-availability-alarm" })
}

resource "aws_cloudwatch_metric_alarm" "api_latency" {
  count = var.observability.operational_alarms_enabled ? 1 : 0

  alarm_name          = "${local.alarm_prefix}-api-latency"
  alarm_description   = "Regional HTTP API p95 latency exceeded the approved threshold."
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  threshold           = var.observability.api_latency_threshold_ms
  treat_missing_data  = "notBreaching"

  namespace          = "AWS/ApiGateway"
  metric_name        = "Latency"
  extended_statistic = "p95"
  period             = 60

  dimensions = {
    ApiId = aws_apigatewayv2_api.regional.id
    Stage = aws_apigatewayv2_stage.default.name
  }

  actions_enabled = length(var.observability.alarm_actions) > 0
  alarm_actions   = var.observability.alarm_actions
  ok_actions      = var.observability.alarm_actions

  tags = merge(local.tags, { Capability = "api-latency-alarm" })
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = var.observability.operational_alarms_enabled ? local.lambda_functions : {}

  alarm_name          = "${local.alarm_prefix}-${replace(each.key, "_", "-")}-errors"
  alarm_description   = "Lambda errors exceeded the approved threshold."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = var.observability.lambda_error_threshold
  treat_missing_data  = "notBreaching"

  namespace   = "AWS/Lambda"
  metric_name = "Errors"
  statistic   = "Sum"
  period      = 60

  dimensions = {
    FunctionName = each.value
  }

  actions_enabled = length(var.observability.alarm_actions) > 0
  alarm_actions   = var.observability.alarm_actions
  ok_actions      = var.observability.alarm_actions

  tags = merge(local.tags, { Capability = "lambda-error-alarm" })
}

resource "aws_cloudwatch_metric_alarm" "processing_queue_age" {
  count = var.observability.operational_alarms_enabled ? 1 : 0

  alarm_name          = "${local.alarm_prefix}-queue-oldest-message"
  alarm_description   = "The oldest processing-queue message exceeded the approved age."
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = var.observability.queue_age_threshold_seconds
  treat_missing_data  = "notBreaching"

  namespace   = "AWS/SQS"
  metric_name = "ApproximateAgeOfOldestMessage"
  statistic   = "Maximum"
  period      = 60

  dimensions = {
    QueueName = aws_sqs_queue.processing.name
  }

  actions_enabled = length(var.observability.alarm_actions) > 0
  alarm_actions   = var.observability.alarm_actions
  ok_actions      = var.observability.alarm_actions

  tags = merge(local.tags, { Capability = "queue-age-alarm" })
}

resource "aws_cloudwatch_metric_alarm" "processing_queue_depth" {
  count = var.observability.operational_alarms_enabled ? 1 : 0

  alarm_name          = "${local.alarm_prefix}-queue-depth"
  alarm_description   = "Visible processing-queue messages exceeded the approved depth."
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  threshold           = var.observability.queue_depth_threshold
  treat_missing_data  = "notBreaching"

  namespace   = "AWS/SQS"
  metric_name = "ApproximateNumberOfMessagesVisible"
  statistic   = "Maximum"
  period      = 60

  dimensions = {
    QueueName = aws_sqs_queue.processing.name
  }

  actions_enabled = length(var.observability.alarm_actions) > 0
  alarm_actions   = var.observability.alarm_actions
  ok_actions      = var.observability.alarm_actions

  tags = merge(local.tags, { Capability = "queue-depth-alarm" })
}

resource "aws_cloudwatch_metric_alarm" "processing_dlq_messages" {
  count = var.observability.operational_alarms_enabled ? 1 : 0

  alarm_name          = "${local.alarm_prefix}-dlq-messages"
  alarm_description   = "One or more messages are visible in the regional dead-letter queue."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  threshold           = 1
  treat_missing_data  = "notBreaching"

  namespace   = "AWS/SQS"
  metric_name = "ApproximateNumberOfMessagesVisible"
  statistic   = "Maximum"
  period      = 60

  dimensions = {
    QueueName = aws_sqs_queue.processing_dlq.name
  }

  actions_enabled = length(var.observability.alarm_actions) > 0
  alarm_actions   = var.observability.alarm_actions
  ok_actions      = var.observability.alarm_actions

  tags = merge(local.tags, { Capability = "dlq-alarm" })
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_throttles" {
  count = var.observability.operational_alarms_enabled ? 1 : 0

  alarm_name          = "${local.alarm_prefix}-dynamodb-throttles"
  alarm_description   = "DynamoDB request throttling occurred in the active Region."
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 0
  treat_missing_data  = "notBreaching"

  namespace   = "AWS/DynamoDB"
  metric_name = "ThrottledRequests"
  statistic   = "Sum"
  period      = 60

  dimensions = {
    TableName = var.data.table_name
  }

  actions_enabled = length(var.observability.alarm_actions) > 0
  alarm_actions   = var.observability.alarm_actions
  ok_actions      = var.observability.alarm_actions

  tags = merge(local.tags, { Capability = "data-throttle-alarm" })
}
