locals {
  operational_alert_email = (
    trimspace(var.operational_alert_email) != ""
    ? trimspace(var.operational_alert_email)
    : trimspace(var.registration_notification_email)
  )

  worker_metric_namespace = "${var.project_name}/${var.environment}"
}

resource "aws_sns_topic" "operational_alerts" {
  name = "${local.name_prefix}-operational-alerts"
}

resource "aws_sns_topic_subscription" "operational_alert_email" {
  count = local.operational_alert_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.operational_alerts.arn
  protocol  = "email"
  endpoint  = local.operational_alert_email
}

resource "aws_cloudwatch_metric_alarm" "worker_record_failures" {
  alarm_name = "${local.name_prefix}-worker-record-failures"

  alarm_description = (
    "One or more SQS records failed during resume-analysis worker processing."
  )

  namespace   = local.worker_metric_namespace
  metric_name = "WorkerRecordFailures"

  dimensions = {
    FunctionName = aws_lambda_function.resume_analysis_worker.function_name
  }

  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"

  treat_missing_data = "notBreaching"

  alarm_actions = [
    aws_sns_topic.operational_alerts.arn
  ]

  ok_actions = [
    aws_sns_topic.operational_alerts.arn
  ]
}

resource "aws_cloudwatch_metric_alarm" "worker_lambda_errors" {
  alarm_name = "${local.name_prefix}-worker-lambda-errors"

  alarm_description = "The worker Lambda invocation failed because of an unhandled, runtime, timeout, or configuration error."

  namespace   = "AWS/Lambda"
  metric_name = "Errors"

  dimensions = {
    FunctionName = aws_lambda_function.resume_analysis_worker.function_name
  }

  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"

  treat_missing_data = "notBreaching"

  alarm_actions = [
    aws_sns_topic.operational_alerts.arn
  ]

  ok_actions = [
    aws_sns_topic.operational_alerts.arn
  ]
}

resource "aws_cloudwatch_metric_alarm" "queue_oldest_message" {
  alarm_name = "${local.name_prefix}-queue-oldest-message"

  alarm_description = "The oldest unprocessed resume-analysis message has remained in the main queue for at least five minutes."

  namespace   = "AWS/SQS"
  metric_name = "ApproximateAgeOfOldestMessage"

  dimensions = {
    QueueName = aws_sqs_queue.resume_analysis_jobs.name
  }

  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 300
  comparison_operator = "GreaterThanOrEqualToThreshold"

  treat_missing_data = "notBreaching"

  alarm_actions = [
    aws_sns_topic.operational_alerts.arn
  ]

  ok_actions = [
    aws_sns_topic.operational_alerts.arn
  ]
}

resource "aws_cloudwatch_metric_alarm" "queue_backlog" {
  alarm_name = "${local.name_prefix}-queue-backlog"

  alarm_description = "At least ten resume-analysis messages have remained available for processing for ten minutes."

  namespace   = "AWS/SQS"
  metric_name = "ApproximateNumberOfMessagesVisible"

  dimensions = {
    QueueName = aws_sqs_queue.resume_analysis_jobs.name
  }

  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 10
  comparison_operator = "GreaterThanOrEqualToThreshold"

  treat_missing_data = "notBreaching"

  alarm_actions = [
    aws_sns_topic.operational_alerts.arn
  ]

  ok_actions = [
    aws_sns_topic.operational_alerts.arn
  ]
}

resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name = "${local.name_prefix}-dlq-messages"

  alarm_description = (
    "One or more resume-analysis messages are present in the dead-letter queue."
  )

  namespace   = "AWS/SQS"
  metric_name = "ApproximateNumberOfMessagesVisible"

  dimensions = {
    QueueName = aws_sqs_queue.resume_analysis_dlq.name
  }

  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"

  treat_missing_data = "notBreaching"

  alarm_actions = [
    aws_sns_topic.operational_alerts.arn
  ]

  ok_actions = [
    aws_sns_topic.operational_alerts.arn
  ]
}

resource "aws_cloudwatch_dashboard" "operations" {
  dashboard_name = "${local.name_prefix}-operations"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 2

        properties = {
          markdown = "# AI Resume Coach — ${var.environment} operations"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 2
        width  = 12
        height = 6

        properties = {
          title  = "Worker failures and runtime errors"
          region = var.aws_region
          period = 300
          stat   = "Sum"

          metrics = [
            [
              local.worker_metric_namespace,
              "WorkerRecordFailures",
              "FunctionName",
              aws_lambda_function.resume_analysis_worker.function_name,
              {
                label = "Failed SQS records"
              }
            ],
            [
              "AWS/Lambda",
              "Errors",
              "FunctionName",
              aws_lambda_function.resume_analysis_worker.function_name,
              {
                label = "Lambda invocation errors"
              }
            ],
            [
              "AWS/Lambda",
              "Throttles",
              "FunctionName",
              aws_lambda_function.resume_analysis_worker.function_name,
              {
                label = "Lambda throttles"
              }
            ]
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 2
        width  = 12
        height = 6

        properties = {
          title  = "Worker duration"
          region = var.aws_region
          period = 300

          metrics = [
            [
              "AWS/Lambda",
              "Duration",
              "FunctionName",
              aws_lambda_function.resume_analysis_worker.function_name,
              {
                stat  = "Average"
                label = "Average duration"
              }
            ],
            [
              "...",
              {
                stat  = "Maximum"
                label = "Maximum duration"
              }
            ]
          ]

          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 8
        width  = 12
        height = 6

        properties = {
          title  = "Main queue depth"
          region = var.aws_region
          period = 60
          stat   = "Maximum"

          metrics = [
            [
              "AWS/SQS",
              "ApproximateNumberOfMessagesVisible",
              "QueueName",
              aws_sqs_queue.resume_analysis_jobs.name,
              {
                label = "Available"
              }
            ],
            [
              ".",
              "ApproximateNumberOfMessagesNotVisible",
              ".",
              ".",
              {
                label = "In flight"
              }
            ],
            [
              ".",
              "ApproximateNumberOfMessagesDelayed",
              ".",
              ".",
              {
                label = "Delayed"
              }
            ]
          ]

          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 8
        width  = 12
        height = 6

        properties = {
          title  = "Oldest queued message"
          region = var.aws_region
          period = 60
          stat   = "Maximum"

          metrics = [
            [
              "AWS/SQS",
              "ApproximateAgeOfOldestMessage",
              "QueueName",
              aws_sqs_queue.resume_analysis_jobs.name,
              {
                label = "Oldest message age"
              }
            ]
          ]

          annotations = {
            horizontal = [
              {
                label = "5-minute threshold"
                value = 300
              }
            ]
          }

          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 14
        width  = 12
        height = 6

        properties = {
          title  = "Dead-letter queue"
          region = var.aws_region
          period = 60
          stat   = "Maximum"

          metrics = [
            [
              "AWS/SQS",
              "ApproximateNumberOfMessagesVisible",
              "QueueName",
              aws_sqs_queue.resume_analysis_dlq.name,
              {
                label = "DLQ messages"
              }
            ]
          ]

          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 14
        width  = 12
        height = 6

        properties = {
          title  = "Worker invocations"
          region = var.aws_region
          period = 300
          stat   = "Sum"

          metrics = [
            [
              "AWS/Lambda",
              "Invocations",
              "FunctionName",
              aws_lambda_function.resume_analysis_worker.function_name,
              {
                label = "Invocations"
              }
            ]
          ]

          yAxis = {
            left = {
              min = 0
            }
          }
        }
      }
    ]
  })
}
