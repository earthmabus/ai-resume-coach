locals {
  function_environment = {
    APP_VERSION                = var.runtime.app_version
    ARCHITECTURE               = var.architecture_version
    DEPLOYMENT_ID              = var.runtime.deployment_id
    ENVIRONMENT                = var.environment
    LOG_LEVEL                  = var.runtime.log_level
    REGION_ROLE                = var.region_role
    SITE_NAME                  = var.site_name
    USER_POOL_ID               = var.identity.user_pool_id
    USER_POOL_CLIENT           = var.identity.client_id
    IDENTITY_ISSUER            = var.identity.issuer
    DOCUMENT_BUCKET            = aws_s3_bucket.documents.bucket
    PROCESSING_QUEUE_URL       = aws_sqs_queue.processing.url
    APPLICATION_TABLE          = var.data.table_name
    DATA_CONSISTENCY           = var.data.consistency_mode
    DATA_WITNESS_REGION        = var.data.witness_region
    TELEMETRY_NAMESPACE        = var.observability.metric_namespace
    STRUCTURED_LOGGING         = tostring(var.observability.structured_logging_enabled)
    CORRELATION_HEADER         = "x-correlation-id"
    REQUEST_ID_FIELD           = "requestId"
    CORRELATION_ID_FIELD       = "correlationId"
    ARCHITECTURE_VERSION_FIELD = var.architecture_version
  }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${local.name_prefix}-api"
  retention_in_days = var.compute.log_retention_days

  tags = merge(local.tags, { Capability = "api-logs" })
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/${local.name_prefix}-worker"
  retention_in_days = var.compute.log_retention_days

  tags = merge(local.tags, { Capability = "worker-logs" })
}

resource "aws_cloudwatch_log_group" "outbox_publisher" {
  name              = "/aws/lambda/${local.name_prefix}-outbox-publisher"
  retention_in_days = var.compute.log_retention_days

  tags = merge(local.tags, { Capability = "outbox-publisher-logs" })
}

resource "aws_lambda_function" "api" {
  function_name = "${local.name_prefix}-api"
  description   = "Regional API application function."
  role          = aws_iam_role.api.arn
  runtime       = var.compute.runtime
  architectures = [var.compute.architecture]
  handler       = "handler.lambda_handler"

  filename         = var.packages.api.filename
  source_code_hash = var.packages.api.source_code_hash

  memory_size = var.compute.api_memory_mb
  timeout     = var.compute.api_timeout_seconds

  tracing_config {
    mode = var.observability.active_tracing_enabled ? "Active" : "PassThrough"
  }


  environment {
    variables = merge(
      local.function_environment,
      {
        FUNCTION_ROLE = "api"
      },
    )
  }

  depends_on = [
    aws_cloudwatch_log_group.api,
    aws_iam_role_policy_attachment.api_basic_execution,
    aws_iam_role_policy.api_runtime,
  ]

  tags = merge(local.tags, { Capability = "regional-api" })
}

resource "aws_lambda_function" "worker" {
  function_name = "${local.name_prefix}-worker"
  description   = "Regional asynchronous processing worker."
  role          = aws_iam_role.worker.arn
  runtime       = var.compute.runtime
  architectures = [var.compute.architecture]
  handler       = "handler.lambda_handler"

  filename         = var.packages.worker.filename
  source_code_hash = var.packages.worker.source_code_hash

  memory_size = var.compute.worker_memory_mb
  timeout     = var.compute.worker_timeout_seconds

  tracing_config {
    mode = var.observability.active_tracing_enabled ? "Active" : "PassThrough"
  }


  environment {
    variables = merge(
      local.function_environment,
      {
        FUNCTION_ROLE = "worker"
      },
    )
  }

  depends_on = [
    aws_cloudwatch_log_group.worker,
    aws_iam_role_policy_attachment.worker_basic_execution,
    aws_iam_role_policy.worker_runtime,
  ]

  tags = merge(local.tags, { Capability = "regional-worker" })
}

resource "aws_lambda_function" "outbox_publisher" {
  function_name = "${local.name_prefix}-outbox-publisher"
  description   = "Regional transactional-outbox publisher."
  role          = aws_iam_role.outbox_publisher.arn
  runtime       = var.compute.runtime
  architectures = [var.compute.architecture]
  handler       = "handler.lambda_handler"

  filename         = var.packages.outbox_publisher.filename
  source_code_hash = var.packages.outbox_publisher.source_code_hash

  memory_size = var.compute.outbox_publisher_memory_mb
  timeout     = var.compute.outbox_publisher_timeout_seconds

  tracing_config {
    mode = var.observability.active_tracing_enabled ? "Active" : "PassThrough"
  }


  environment {
    variables = merge(
      local.function_environment,
      {
        FUNCTION_ROLE = "outbox-publisher"
      },
    )
  }

  depends_on = [
    aws_cloudwatch_log_group.outbox_publisher,
    aws_iam_role_policy_attachment.outbox_publisher_basic_execution,
    aws_iam_role_policy.outbox_publisher_runtime,
  ]

  tags = merge(local.tags, { Capability = "regional-outbox-publisher" })
}

resource "aws_lambda_event_source_mapping" "worker_processing_queue" {
  event_source_arn = aws_sqs_queue.processing.arn
  function_name    = aws_lambda_function.worker.arn

  batch_size                         = var.compute.worker_batch_size
  maximum_batching_window_in_seconds = var.compute.worker_maximum_batching_window_seconds
  function_response_types            = ["ReportBatchItemFailures"]
  enabled                            = true
}

resource "aws_cloudwatch_event_target" "outbox_publisher" {
  rule = aws_cloudwatch_event_rule.outbox_publisher_schedule.name
  arn  = aws_lambda_function.outbox_publisher.arn

  target_id = "regional-outbox-publisher"
}

resource "aws_lambda_permission" "eventbridge_outbox_publisher" {
  statement_id  = "AllowEventBridgeOutboxPublisher"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.outbox_publisher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.outbox_publisher_schedule.arn
}
