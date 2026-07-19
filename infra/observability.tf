locals {
  telemetry_log_schema_fields = [
    "timestamp",
    "level",
    "service",
    "component",
    "operation",
    "requestId",
    "correlationId",
    "deploymentId",
    "region",
    "site",
    "userId",
    "tenantId",
    "durationMs",
    "result",
    "errorCode",
    "architectureVersion",
  ]

  telemetry_never_logged_fields = [
    "authorization",
    "password",
    "accessToken",
    "refreshToken",
    "apiKey",
    "resumeText",
  ]

  observability_dashboard_name = "${local.global_name_prefix}-platform-operations"

  regional_alarm_names = sort(concat(
    module.east.observability.alarms.names,
    module.west.observability.alarms.names,
  ))
}

resource "aws_cloudwatch_dashboard" "platform_operations" {
  count = var.enable_observability_dashboard ? 1 : 0

  dashboard_name = local.observability_dashboard_name

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 2
        properties = {
          markdown = "# AI Resume Coach Platform V2 — Operations\nActive-active sites: us-east-1 and us-west-2"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 2
        width  = 12
        height = 6
        properties = {
          title  = "Regional API Requests and 5XX"
          view   = "timeSeries"
          region = local.sites.east.region
          period = 60
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiId", module.east.api_gateway.id, "Stage", module.east.api_gateway.stage.name, { label = "East requests" }],
            [".", "5xx", ".", ".", ".", ".", { label = "East 5XX" }],
            ["AWS/ApiGateway", "Count", "ApiId", module.west.api_gateway.id, "Stage", module.west.api_gateway.stage.name, { label = "West requests", region = local.sites.west.region }],
            [".", "5xx", ".", ".", ".", ".", { label = "West 5XX", region = local.sites.west.region }],
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
          title  = "Regional API Latency"
          view   = "timeSeries"
          region = local.sites.east.region
          stat   = "p95"
          period = 60
          metrics = [
            ["AWS/ApiGateway", "Latency", "ApiId", module.east.api_gateway.id, "Stage", module.east.api_gateway.stage.name, { label = "East p95" }],
            ["AWS/ApiGateway", "Latency", "ApiId", module.west.api_gateway.id, "Stage", module.west.api_gateway.stage.name, { label = "West p95", region = local.sites.west.region }],
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 8
        width  = 12
        height = 6
        properties = {
          title  = "Lambda Errors"
          view   = "timeSeries"
          region = local.sites.east.region
          period = 60
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", module.east.compute.api.name, { label = "East API" }],
            [".", ".", ".", module.east.compute.worker.name, { label = "East worker" }],
            [".", ".", ".", module.west.compute.api.name, { label = "West API", region = local.sites.west.region }],
            [".", ".", ".", module.west.compute.worker.name, { label = "West worker", region = local.sites.west.region }],
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 8
        width  = 12
        height = 6
        properties = {
          title  = "Processing Queue Health"
          view   = "timeSeries"
          region = local.sites.east.region
          period = 60
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", module.east.processing_queue.name, { label = "East queue depth" }],
            [".", "ApproximateAgeOfOldestMessage", ".", ".", { label = "East oldest age" }],
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", module.west.processing_queue.name, { label = "West queue depth", region = local.sites.west.region }],
            [".", "ApproximateAgeOfOldestMessage", ".", ".", { label = "West oldest age", region = local.sites.west.region }],
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 14
        width  = 12
        height = 6
        properties = {
          title  = "DynamoDB Throttles"
          view   = "timeSeries"
          region = local.sites.east.region
          period = 60
          metrics = [
            ["AWS/DynamoDB", "ThrottledRequests", "TableName", module.shared_foundation.resume_analysis.name, { label = "East throttles" }],
            ["AWS/DynamoDB", "ThrottledRequests", "TableName", module.shared_foundation.resume_analysis.name, { label = "West throttles", region = local.sites.west.region }],
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 14
        width  = 12
        height = 6
        properties = {
          title  = "Synthetic Health Success"
          view   = "timeSeries"
          region = local.sites.east.region
          period = 300
          metrics = var.enable_synthetic_monitoring ? [
            ["CloudWatchSynthetics", "SuccessPercent", "CanaryName", aws_synthetics_canary.east[0].name, { label = "East health" }],
            ["CloudWatchSynthetics", "SuccessPercent", "CanaryName", aws_synthetics_canary.west[0].name, { label = "West health", region = local.sites.west.region }],
          ] : []
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 20
        width  = 12
        height = 6
        properties = {
          title  = "Lambda Throttles"
          view   = "timeSeries"
          region = local.sites.east.region
          period = 60
          metrics = [
            ["AWS/Lambda", "Throttles", "FunctionName", module.east.compute.api.name, { label = "East API" }],
            [".", ".", ".", module.east.compute.worker.name, { label = "East worker" }],
            [".", ".", ".", module.east.compute.outbox_publisher.name, { label = "East outbox publisher" }],
            ["AWS/Lambda", "Throttles", "FunctionName", module.west.compute.api.name, { label = "West API", region = local.sites.west.region }],
            [".", ".", ".", module.west.compute.worker.name, { label = "West worker", region = local.sites.west.region }],
            [".", ".", ".", module.west.compute.outbox_publisher.name, { label = "West outbox publisher", region = local.sites.west.region }],
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 20
        width  = 12
        height = 6
        properties = {
          title  = "Worker and Outbox Failure Metrics"
          view   = "timeSeries"
          region = local.sites.east.region
          period = 300
          metrics = [
            [var.telemetry_metric_namespace, "WorkerRecordFailures", "FunctionName", module.east.compute.worker.name, { label = "East worker record failures" }],
            [".", "OutboxPublishFailures", ".", module.east.compute.outbox_publisher.name, { label = "East outbox publish failures" }],
            [var.telemetry_metric_namespace, "WorkerRecordFailures", "FunctionName", module.west.compute.worker.name, { label = "West worker record failures", region = local.sites.west.region }],
            [".", "OutboxPublishFailures", ".", module.west.compute.outbox_publisher.name, { label = "West outbox publish failures", region = local.sites.west.region }],
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 26
        width  = 12
        height = 6
        properties = {
          title  = "Processing DLQ Depth"
          view   = "timeSeries"
          region = local.sites.east.region
          period = 60
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", module.east.processing_dlq.name, { label = "East DLQ depth" }],
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", module.west.processing_dlq.name, { label = "West DLQ depth", region = local.sites.west.region }],
          ]
        }
      },
      {
        type   = "log"
        x      = 12
        y      = 26
        width  = 12
        height = 6
        properties = {
          title  = "Recent Regional Application Errors"
          region = local.sites.east.region
          query = join(
            "\n",
            [
              "SOURCE '${module.east.compute.api.log_group}' | SOURCE '${module.east.compute.worker.log_group}'",
              "| fields @timestamp, level, service, operation, requestId, correlationId, result, errorCode, @message",
              "| filter level = 'ERROR' or result = 'FAILURE'",
              "| sort @timestamp desc",
              "| limit 50",
            ],
          )
          view = "table"
        }
      },
    ]
  })
}

resource "aws_s3_bucket" "synthetic_artifacts_east" {
  count    = var.enable_synthetic_monitoring ? 1 : 0
  provider = aws.us_east_1

  bucket_prefix = "${local.global_name_prefix}-synthetics-east-"
  force_destroy = true

  tags = merge(local.common_tags, {
    Scope      = "regional"
    Site       = "east"
    Capability = "synthetic-artifacts"
  })
}

resource "aws_s3_bucket" "synthetic_artifacts_west" {
  count    = var.enable_synthetic_monitoring ? 1 : 0
  provider = aws.us_west_2

  bucket_prefix = "${local.global_name_prefix}-synthetics-west-"
  force_destroy = true

  tags = merge(local.common_tags, {
    Scope      = "regional"
    Site       = "west"
    Capability = "synthetic-artifacts"
  })
}

resource "aws_s3_bucket_public_access_block" "synthetic_artifacts_east" {
  count    = var.enable_synthetic_monitoring ? 1 : 0
  provider = aws.us_east_1

  bucket = aws_s3_bucket.synthetic_artifacts_east[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "synthetic_artifacts_west" {
  count    = var.enable_synthetic_monitoring ? 1 : 0
  provider = aws.us_west_2

  bucket = aws_s3_bucket.synthetic_artifacts_west[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "synthetic_artifacts_east" {
  count    = var.enable_synthetic_monitoring ? 1 : 0
  provider = aws.us_east_1

  bucket = aws_s3_bucket.synthetic_artifacts_east[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "synthetic_artifacts_west" {
  count    = var.enable_synthetic_monitoring ? 1 : 0
  provider = aws.us_west_2

  bucket = aws_s3_bucket.synthetic_artifacts_west[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "synthetic_artifacts_east" {
  count    = var.enable_synthetic_monitoring ? 1 : 0
  provider = aws.us_east_1

  bucket = aws_s3_bucket.synthetic_artifacts_east[0].id

  rule {
    id     = "expire-synthetic-artifacts"
    status = "Enabled"

    filter {}

    expiration {
      days = var.synthetic_artifact_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.synthetic_artifact_retention_days
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "synthetic_artifacts_west" {
  count    = var.enable_synthetic_monitoring ? 1 : 0
  provider = aws.us_west_2

  bucket = aws_s3_bucket.synthetic_artifacts_west[0].id

  rule {
    id     = "expire-synthetic-artifacts"
    status = "Enabled"

    filter {}

    expiration {
      days = var.synthetic_artifact_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.synthetic_artifact_retention_days
    }
  }
}

resource "aws_iam_role" "synthetic_east" {
  count    = var.enable_synthetic_monitoring ? 1 : 0
  provider = aws.us_east_1

  name = "${local.global_name_prefix}-synthetic-east"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = merge(local.common_tags, {
    Scope      = "regional"
    Site       = "east"
    Capability = "synthetic-monitoring"
  })
}

resource "aws_iam_role" "synthetic_west" {
  count    = var.enable_synthetic_monitoring ? 1 : 0
  provider = aws.us_west_2

  name = "${local.global_name_prefix}-synthetic-west"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = merge(local.common_tags, {
    Scope      = "regional"
    Site       = "west"
    Capability = "synthetic-monitoring"
  })
}

resource "aws_iam_role_policy" "synthetic_east" {
  count    = var.enable_synthetic_monitoring ? 1 : 0
  provider = aws.us_east_1

  name = "${local.global_name_prefix}-synthetic-east"
  role = aws_iam_role.synthetic_east[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetBucketLocation",
          "s3:ListAllMyBuckets",
        ]
        Resource = [
          aws_s3_bucket.synthetic_artifacts_east[0].arn,
          "${aws_s3_bucket.synthetic_artifacts_east[0].arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "xray:PutTraceSegments",
        ]
        Resource = "*"
      },
    ]
  })
}

resource "aws_iam_role_policy" "synthetic_west" {
  count    = var.enable_synthetic_monitoring ? 1 : 0
  provider = aws.us_west_2

  name = "${local.global_name_prefix}-synthetic-west"
  role = aws_iam_role.synthetic_west[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetBucketLocation",
          "s3:ListAllMyBuckets",
        ]
        Resource = [
          aws_s3_bucket.synthetic_artifacts_west[0].arn,
          "${aws_s3_bucket.synthetic_artifacts_west[0].arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "xray:PutTraceSegments",
        ]
        Resource = "*"
      },
    ]
  })
}

resource "aws_synthetics_canary" "east" {
  count    = var.enable_synthetic_monitoring ? 1 : 0
  provider = aws.us_east_1

  name                 = substr("${local.global_name_prefix}-east-health", 0, 21)
  artifact_s3_location = "s3://${aws_s3_bucket.synthetic_artifacts_east[0].bucket}/"
  execution_role_arn   = aws_iam_role.synthetic_east[0].arn
  handler              = "health.handler"
  runtime_version      = var.synthetic_runtime_version
  zip_file             = data.archive_file.synthetic_health_zip.output_path


  schedule {
    expression = var.synthetic_schedule_expression
  }

  run_config {
    timeout_in_seconds = var.synthetic_timeout_seconds

    environment_variables = {
      API_ENDPOINT = module.east.api_gateway.endpoint
      SITE         = "east"
    }
  }

  tags = merge(local.common_tags, {
    Scope      = "regional"
    Site       = "east"
    Capability = "synthetic-monitoring"
  })
}

resource "aws_synthetics_canary" "west" {
  count    = var.enable_synthetic_monitoring ? 1 : 0
  provider = aws.us_west_2

  name                 = substr("${local.global_name_prefix}-west-health", 0, 21)
  artifact_s3_location = "s3://${aws_s3_bucket.synthetic_artifacts_west[0].bucket}/"
  execution_role_arn   = aws_iam_role.synthetic_west[0].arn
  handler              = "health.handler"
  runtime_version      = var.synthetic_runtime_version
  zip_file             = data.archive_file.synthetic_health_zip.output_path


  schedule {
    expression = var.synthetic_schedule_expression
  }

  run_config {
    timeout_in_seconds = var.synthetic_timeout_seconds

    environment_variables = {
      API_ENDPOINT = module.west.api_gateway.endpoint
      SITE         = "west"
    }
  }

  tags = merge(local.common_tags, {
    Scope      = "regional"
    Site       = "west"
    Capability = "synthetic-monitoring"
  })
}
