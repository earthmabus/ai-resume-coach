module "east" {
  source = "./modules/regional_application"

  providers = {
    aws = aws.us_east_1
  }

  project_name         = var.project_name
  environment          = var.environment
  architecture_version = local.architecture_version

  site_name   = "east"
  region      = local.sites.east.region
  region_code = local.sites.east.region_code
  region_role = local.sites.east.role


  identity = {
    user_pool_id = aws_cognito_user_pool.users.id
    client_id    = aws_cognito_user_pool_client.web.id
    issuer = join(
      "",
      [
        "https://cognito-idp.us-east-1.amazonaws.com/",
        aws_cognito_user_pool.users.id,
      ],
    )
  }


  storage = {
    force_destroy                      = var.document_bucket_force_destroy
    noncurrent_version_expiration_days = var.document_noncurrent_version_expiration_days
  }

  messaging = {
    visibility_timeout_seconds = var.processing_queue_visibility_timeout_seconds
    queue_retention_seconds    = var.processing_queue_message_retention_seconds
    dlq_retention_seconds      = var.processing_dlq_message_retention_seconds
    max_receive_count          = var.processing_queue_max_receive_count
    publisher_schedule         = var.outbox_publisher_schedule_expression
  }

  packages = {
    api = {
      filename         = data.archive_file.api_zip.output_path
      source_code_hash = data.archive_file.api_zip.output_base64sha256
    }
    worker = {
      filename         = data.archive_file.worker_zip.output_path
      source_code_hash = data.archive_file.worker_zip.output_base64sha256
    }
    outbox_publisher = {
      filename         = data.archive_file.outbox_publisher_zip.output_path
      source_code_hash = data.archive_file.outbox_publisher_zip.output_base64sha256
    }
  }

  compute = {
    runtime                                = var.lambda_runtime
    architecture                           = var.lambda_architecture
    log_retention_days                     = var.lambda_log_retention_days
    api_memory_mb                          = var.api_lambda_memory_mb
    api_timeout_seconds                    = var.api_lambda_timeout_seconds
    worker_memory_mb                       = var.worker_lambda_memory_mb
    worker_timeout_seconds                 = var.worker_lambda_timeout_seconds
    outbox_publisher_memory_mb             = var.outbox_publisher_lambda_memory_mb
    outbox_publisher_timeout_seconds       = var.outbox_publisher_lambda_timeout_seconds
    worker_batch_size                      = var.worker_batch_size
    worker_maximum_batching_window_seconds = var.worker_maximum_batching_window_seconds
  }

  data = {
    table_name         = local.application_table.name
    regional_table_arn = local.application_table_regional_arns.east
    consistency_mode   = local.application_table.consistency_mode
    witness_region     = local.application_table.witness_region
  }

  api = {
    cors_allowed_origins      = var.api_cors_allowed_origins
    throttling_burst_limit    = var.api_throttling_burst_limit
    throttling_rate_limit     = var.api_throttling_rate_limit
    access_log_retention_days = var.api_access_log_retention_days
  }

  observability = {
    metric_namespace            = var.telemetry_metric_namespace
    structured_logging_enabled  = var.enable_structured_logging
    active_tracing_enabled      = var.enable_active_tracing
    operational_alarms_enabled  = var.enable_operational_alarms
    alarm_actions               = var.observability_alarm_actions
    api_5xx_threshold           = var.api_5xx_alarm_threshold
    api_latency_threshold_ms    = var.api_latency_alarm_threshold_ms
    lambda_error_threshold      = var.lambda_error_alarm_threshold
    queue_age_threshold_seconds = var.queue_age_alarm_threshold_seconds
    queue_depth_threshold       = var.queue_depth_alarm_threshold
  }

  runtime = local.application_runtime
  common_tags = merge(
    local.common_tags,
    {
      Scope = "regional"
      Site  = "east"
    },
  )
}

module "west" {
  source = "./modules/regional_application"

  providers = {
    aws = aws.us_west_2
  }

  project_name         = var.project_name
  environment          = var.environment
  architecture_version = local.architecture_version

  site_name   = "west"
  region      = local.sites.west.region
  region_code = local.sites.west.region_code
  region_role = local.sites.west.role


  identity = {
    user_pool_id = aws_cognito_user_pool.users.id
    client_id    = aws_cognito_user_pool_client.web.id
    issuer = join(
      "",
      [
        "https://cognito-idp.us-east-1.amazonaws.com/",
        aws_cognito_user_pool.users.id,
      ],
    )
  }


  storage = {
    force_destroy                      = var.document_bucket_force_destroy
    noncurrent_version_expiration_days = var.document_noncurrent_version_expiration_days
  }

  messaging = {
    visibility_timeout_seconds = var.processing_queue_visibility_timeout_seconds
    queue_retention_seconds    = var.processing_queue_message_retention_seconds
    dlq_retention_seconds      = var.processing_dlq_message_retention_seconds
    max_receive_count          = var.processing_queue_max_receive_count
    publisher_schedule         = var.outbox_publisher_schedule_expression
  }

  packages = {
    api = {
      filename         = data.archive_file.api_zip.output_path
      source_code_hash = data.archive_file.api_zip.output_base64sha256
    }
    worker = {
      filename         = data.archive_file.worker_zip.output_path
      source_code_hash = data.archive_file.worker_zip.output_base64sha256
    }
    outbox_publisher = {
      filename         = data.archive_file.outbox_publisher_zip.output_path
      source_code_hash = data.archive_file.outbox_publisher_zip.output_base64sha256
    }
  }

  compute = {
    runtime                                = var.lambda_runtime
    architecture                           = var.lambda_architecture
    log_retention_days                     = var.lambda_log_retention_days
    api_memory_mb                          = var.api_lambda_memory_mb
    api_timeout_seconds                    = var.api_lambda_timeout_seconds
    worker_memory_mb                       = var.worker_lambda_memory_mb
    worker_timeout_seconds                 = var.worker_lambda_timeout_seconds
    outbox_publisher_memory_mb             = var.outbox_publisher_lambda_memory_mb
    outbox_publisher_timeout_seconds       = var.outbox_publisher_lambda_timeout_seconds
    worker_batch_size                      = var.worker_batch_size
    worker_maximum_batching_window_seconds = var.worker_maximum_batching_window_seconds
  }

  data = {
    table_name         = local.application_table.name
    regional_table_arn = local.application_table_regional_arns.west
    consistency_mode   = local.application_table.consistency_mode
    witness_region     = local.application_table.witness_region
  }

  api = {
    cors_allowed_origins      = var.api_cors_allowed_origins
    throttling_burst_limit    = var.api_throttling_burst_limit
    throttling_rate_limit     = var.api_throttling_rate_limit
    access_log_retention_days = var.api_access_log_retention_days
  }

  observability = {
    metric_namespace            = var.telemetry_metric_namespace
    structured_logging_enabled  = var.enable_structured_logging
    active_tracing_enabled      = var.enable_active_tracing
    operational_alarms_enabled  = var.enable_operational_alarms
    alarm_actions               = var.observability_alarm_actions
    api_5xx_threshold           = var.api_5xx_alarm_threshold
    api_latency_threshold_ms    = var.api_latency_alarm_threshold_ms
    lambda_error_threshold      = var.lambda_error_alarm_threshold
    queue_age_threshold_seconds = var.queue_age_alarm_threshold_seconds
    queue_depth_threshold       = var.queue_depth_alarm_threshold
  }

  runtime = local.application_runtime
  common_tags = merge(
    local.common_tags,
    {
      Scope = "regional"
      Site  = "west"
    },
  )
}
