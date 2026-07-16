locals {
  operational_alert_email = (
    trimspace(var.operational_alert_email) != ""
    ? trimspace(var.operational_alert_email)
    : trimspace(var.registration_notification_email)
  )

  application_metric_namespace = "${var.project_name}/${var.environment}"

  outbox_publisher_function_name = "${local.name_prefix}-outbox-publisher"
  outbox_publisher_schedule_name = "${local.name_prefix}-outbox-publisher-schedule"
  worker_function_name           = "${local.name_prefix}-resume-analysis-worker"
  processing_queue_name          = "${local.name_prefix}-resume-analysis-jobs"
  processing_dlq_name            = "${local.name_prefix}-resume-analysis-dlq"

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

  namespace   = local.application_metric_namespace
  metric_name = "WorkerRecordFailures"

  dimensions = {
    FunctionName = local.worker_function_name
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
    FunctionName = local.worker_function_name
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
    QueueName = local.processing_queue_name
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
    QueueName = local.processing_queue_name
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
    QueueName = local.processing_dlq_name
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

resource "aws_cloudwatch_metric_alarm" "outbox_publish_failures" {
  alarm_name = "${local.name_prefix}-outbox-publish-failures"

  alarm_description = (
    "One or more transactional outbox events failed to publish to SQS."
  )

  namespace   = local.application_metric_namespace
  metric_name = "OutboxPublishFailures"

  dimensions = {
    FunctionName = local.outbox_publisher_function_name
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

resource "aws_cloudwatch_metric_alarm" "outbox_permanent_failures" {
  alarm_name = "${local.name_prefix}-outbox-permanent-failures"

  alarm_description = (
    "One or more transactional outbox events reached the permanent-failure state."
  )

  namespace   = local.application_metric_namespace
  metric_name = "OutboxPermanentFailures"

  dimensions = {
    FunctionName = local.outbox_publisher_function_name
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

resource "aws_cloudwatch_metric_alarm" "outbox_publisher_lambda_errors" {
  alarm_name = "${local.name_prefix}-outbox-publisher-lambda-errors"

  alarm_description = (
    "The outbox publisher Lambda failed because of an unhandled, runtime, timeout, or configuration error."
  )

  namespace   = "AWS/Lambda"
  metric_name = "Errors"

  dimensions = {
    FunctionName = local.outbox_publisher_function_name
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

resource "aws_cloudwatch_metric_alarm" "outbox_publisher_throttles" {
  alarm_name = "${local.name_prefix}-outbox-publisher-throttles"

  alarm_description = (
    "The outbox publisher Lambda was throttled one or more times."
  )

  namespace   = "AWS/Lambda"
  metric_name = "Throttles"

  dimensions = {
    FunctionName = local.outbox_publisher_function_name
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

resource "aws_cloudwatch_metric_alarm" "outbox_schedule_failed_invocations" {
  alarm_name = "${local.name_prefix}-outbox-schedule-failed-invocations"

  alarm_description = (
    "EventBridge failed to invoke the transactional outbox publisher."
  )

  namespace   = "AWS/Events"
  metric_name = "FailedInvocations"

  dimensions = {
    RuleName = local.outbox_publisher_schedule_name
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
          title  = "Outbox publisher outcomes"
          region = var.aws_region
          period = 300
          stat   = "Sum"

          metrics = [
            [
              local.application_metric_namespace,
              "OutboxEventsExamined",
              "FunctionName",
              local.outbox_publisher_function_name,
              {
                label = "Examined"
              }
            ],
            [
              ".",
              "OutboxEventsClaimed",
              ".",
              ".",
              {
                label = "Claimed"
              }
            ],
            [
              ".",
              "OutboxEventsPublished",
              ".",
              ".",
              {
                label = "Published"
              }
            ],
            [
              ".",
              "OutboxPublishFailures",
              ".",
              ".",
              {
                label = "Publish failures"
              }
            ],
            [
              ".",
              "OutboxPermanentFailures",
              ".",
              ".",
              {
                label = "Permanent failures"
              }
            ],
            [
              ".",
              "OutboxClaimSkips",
              ".",
              ".",
              {
                label = "Claim skips"
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
        y      = 2
        width  = 12
        height = 6

        properties = {
          title  = "Outbox publisher Lambda health"
          region = var.aws_region
          period = 300
          stat   = "Sum"

          metrics = [
            [
              "AWS/Lambda",
              "Invocations",
              "FunctionName",
              local.outbox_publisher_function_name,
              {
                label = "Invocations"
              }
            ],
            [
              ".",
              "Errors",
              ".",
              ".",
              {
                label = "Errors"
              }
            ],
            [
              ".",
              "Throttles",
              ".",
              ".",
              {
                label = "Throttles"
              }
            ],
            [
              ".",
              "Duration",
              ".",
              ".",
              {
                stat  = "Average"
                label = "Average duration"
                yAxis = "right"
              }
            ]
          ]

          yAxis = {
            left = {
              min = 0
            }
            right = {
              min = 0
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 8
        width  = 24
        height = 4

        properties = {
          title  = "Outbox publisher heartbeat"
          region = var.aws_region
          period = 300
          stat   = "Sum"

          metrics = [
            [
              local.application_metric_namespace,
              "OutboxPublisherCycles",
              "FunctionName",
              local.outbox_publisher_function_name,
              {
                label = "Completed publisher cycles"
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
        y      = 12
        width  = 12
        height = 6

        properties = {
          title  = "Worker failures and runtime errors"
          region = var.aws_region
          period = 300
          stat   = "Sum"

          metrics = [
            [
              local.application_metric_namespace,
              "WorkerRecordFailures",
              "FunctionName",
              local.worker_function_name,
              {
                label = "Failed SQS records"
              }
            ],
            [
              "AWS/Lambda",
              "Errors",
              "FunctionName",
              local.worker_function_name,
              {
                label = "Lambda invocation errors"
              }
            ],
            [
              "AWS/Lambda",
              "Throttles",
              "FunctionName",
              local.worker_function_name,
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
        y      = 12
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
              local.worker_function_name,
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
        y      = 18
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
              local.processing_queue_name,
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
        y      = 18
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
              local.processing_queue_name,
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
        y      = 24
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
              local.processing_dlq_name,
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
        y      = 24
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
              local.worker_function_name,
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
