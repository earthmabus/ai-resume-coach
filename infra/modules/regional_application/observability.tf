locals {
  lambda_functions = {
    api              = aws_lambda_function.api.function_name
    worker           = aws_lambda_function.worker.function_name
    outbox_publisher = aws_lambda_function.outbox_publisher.function_name
  }

  alarm_tags = merge(
    local.tags,
    {
      Capability = "regional-operational-alarm"
    },
  )
}

resource "aws_cloudwatch_metric_alarm" "api_5xx" {
  count = var.observability.operational_alarms_enabled ? 1 : 0

  alarm_name        = "${local.name_prefix}-api-5xx"
  alarm_description = "The regional HTTP API returned an elevated number of server errors."

  namespace   = "AWS/ApiGateway"
  metric_name = "5xx"
  statistic   = "Sum"
  period      = 300

  evaluation_periods  = 1
  datapoints_to_alarm = 1

  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = var.observability.api_5xx_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = aws_apigatewayv2_api.regional.id
    Stage = aws_apigatewayv2_stage.default.name
  }

  alarm_actions = var.observability.alarm_actions
  ok_actions    = var.observability.alarm_actions

  tags = local.alarm_tags
}

resource "aws_cloudwatch_metric_alarm" "api_latency" {
  count = var.observability.operational_alarms_enabled ? 1 : 0

  alarm_name        = "${local.name_prefix}-api-latency"
  alarm_description = "The regional HTTP API exceeded the configured latency threshold."

  namespace          = "AWS/ApiGateway"
  metric_name        = "Latency"
  extended_statistic = "p95"
  period             = 300

  evaluation_periods  = 1
  datapoints_to_alarm = 1

  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = var.observability.api_latency_threshold_ms
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = aws_apigatewayv2_api.regional.id
    Stage = aws_apigatewayv2_stage.default.name
  }

  alarm_actions = var.observability.alarm_actions
  ok_actions    = var.observability.alarm_actions

  tags = local.alarm_tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = var.observability.operational_alarms_enabled ? local.lambda_functions : {}

  alarm_name        = "${local.name_prefix}-${replace(each.key, "_", "-")}-errors"
  alarm_description = "The ${replace(each.key, "_", " ")} Lambda reported an elevated number of errors."

  namespace   = "AWS/Lambda"
  metric_name = "Errors"
  statistic   = "Sum"
  period      = 300

  evaluation_periods  = 1
  datapoints_to_alarm = 1

  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = var.observability.lambda_error_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = each.value
  }

  alarm_actions = var.observability.alarm_actions
  ok_actions    = var.observability.alarm_actions

  tags = local.alarm_tags
}

resource "aws_cloudwatch_metric_alarm" "processing_queue_age" {
  count = var.observability.operational_alarms_enabled ? 1 : 0

  alarm_name        = "${local.name_prefix}-processing-queue-age"
  alarm_description = "The oldest Resume Analysis queue message exceeded the configured age threshold."

  namespace   = "AWS/SQS"
  metric_name = "ApproximateAgeOfOldestMessage"
  statistic   = "Maximum"
  period      = 300

  evaluation_periods  = 1
  datapoints_to_alarm = 1

  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = var.observability.queue_age_threshold_seconds
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.processing.name
  }

  alarm_actions = var.observability.alarm_actions
  ok_actions    = var.observability.alarm_actions

  tags = local.alarm_tags
}

resource "aws_cloudwatch_metric_alarm" "processing_queue_depth" {
  count = var.observability.operational_alarms_enabled ? 1 : 0

  alarm_name        = "${local.name_prefix}-processing-queue-depth"
  alarm_description = "The Resume Analysis queue exceeded the configured visible-message threshold."

  namespace   = "AWS/SQS"
  metric_name = "ApproximateNumberOfMessagesVisible"
  statistic   = "Maximum"
  period      = 300

  evaluation_periods  = 1
  datapoints_to_alarm = 1

  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = var.observability.queue_depth_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.processing.name
  }

  alarm_actions = var.observability.alarm_actions
  ok_actions    = var.observability.alarm_actions

  tags = local.alarm_tags
}

resource "aws_cloudwatch_metric_alarm" "processing_dlq_messages" {
  count = var.observability.operational_alarms_enabled ? 1 : 0

  alarm_name        = "${local.name_prefix}-processing-dlq-messages"
  alarm_description = "One or more Resume Analysis messages are visible in the dead-letter queue."

  namespace   = "AWS/SQS"
  metric_name = "ApproximateNumberOfMessagesVisible"
  statistic   = "Maximum"
  period      = 300

  evaluation_periods  = 1
  datapoints_to_alarm = 1

  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.processing_dlq.name
  }

  alarm_actions = var.observability.alarm_actions
  ok_actions    = var.observability.alarm_actions

  tags = local.alarm_tags
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_throttles" {
  count = var.observability.operational_alarms_enabled ? 1 : 0

  alarm_name        = "${local.name_prefix}-resume-analysis-dynamodb-throttles"
  alarm_description = "The regional Resume Analysis DynamoDB replica reported throttled requests."

  namespace   = "AWS/DynamoDB"
  metric_name = "ThrottledRequests"
  statistic   = "Sum"
  period      = 300

  evaluation_periods  = 1
  datapoints_to_alarm = 1

  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = var.resume_analysis.table_name
  }

  alarm_actions = var.observability.alarm_actions
  ok_actions    = var.observability.alarm_actions

  tags = local.alarm_tags
}

resource "aws_cloudwatch_metric_alarm" "worker_record_failures" {
  count = var.observability.operational_alarms_enabled ? 1 : 0

  alarm_name        = "${local.name_prefix}-worker-record-failures"
  alarm_description = "The worker reported sustained per-record processing failures."

  namespace   = var.observability.metric_namespace
  metric_name = "WorkerRecordFailures"
  statistic   = "Sum"
  period      = 300

  evaluation_periods  = 2
  datapoints_to_alarm = 2

  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.worker.function_name
  }

  alarm_actions = var.observability.alarm_actions
  ok_actions    = var.observability.alarm_actions

  tags = local.alarm_tags
}

resource "aws_cloudwatch_metric_alarm" "outbox_publish_failures" {
  count = var.observability.operational_alarms_enabled ? 1 : 0

  alarm_name        = "${local.name_prefix}-outbox-publish-failures"
  alarm_description = "The outbox publisher reported sustained dispatch failures, including local or regional SQS delivery failures."

  namespace   = var.observability.metric_namespace
  metric_name = "OutboxPublishFailures"
  statistic   = "Sum"
  period      = 300

  evaluation_periods  = 2
  datapoints_to_alarm = 2

  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.outbox_publisher.function_name
  }

  alarm_actions = var.observability.alarm_actions
  ok_actions    = var.observability.alarm_actions

  tags = local.alarm_tags
}
