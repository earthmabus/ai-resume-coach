output "site_name" {
  value = var.site_name
}

output "region" {
  value = var.region
}

output "region_code" {
  value = var.region_code
}

output "name_prefix" {
  value = local.name_prefix
}

output "site_identity" {
  value = local.site_identity
}

output "routing" {
  value = {
    current_region    = var.region
    primary_region    = var.routing.primary_region
    secondary_regions = var.routing.secondary_regions
    site_name         = var.site_name
    region_role       = var.region_role
  }
}

output "document_bucket" {
  value = {
    name = aws_s3_bucket.documents.bucket
    arn  = aws_s3_bucket.documents.arn
  }
}

output "processing_queue" {
  value = {
    name = aws_sqs_queue.processing.name
    arn  = aws_sqs_queue.processing.arn
    url  = aws_sqs_queue.processing.url
  }
}

output "processing_dlq" {
  value = {
    name = aws_sqs_queue.processing_dlq.name
    arn  = aws_sqs_queue.processing_dlq.arn
    url  = aws_sqs_queue.processing_dlq.url
  }
}

output "outbox_publisher_schedule" {
  value = {
    name                = aws_cloudwatch_event_rule.outbox_publisher_schedule.name
    schedule_expression = aws_cloudwatch_event_rule.outbox_publisher_schedule.schedule_expression
    state               = aws_cloudwatch_event_rule.outbox_publisher_schedule.state
  }
}

output "regional_transport" {
  value = {
    processing_queue_names_by_region = var.regional_transport.processing_queue_names_by_region
  }
}

output "execution_roles" {
  value = {
    api              = aws_iam_role.api.arn
    worker           = aws_iam_role.worker.arn
    outbox_publisher = aws_iam_role.outbox_publisher.arn
  }
}

output "api_endpoint" {
  description = "Direct regional HTTP API endpoint."
  value       = aws_apigatewayv2_api.regional.api_endpoint
}

output "compute" {
  value = {
    api = {
      name                   = aws_lambda_function.api.function_name
      runtime                = aws_lambda_function.api.runtime
      architecture           = aws_lambda_function.api.architectures[0]
      memory_mb              = aws_lambda_function.api.memory_size
      timeout                = aws_lambda_function.api.timeout
      log_group              = aws_cloudwatch_log_group.api.name
      dependency_layer_count = length(coalesce(aws_lambda_function.api.layers, []))
      dependency_layers      = coalesce(aws_lambda_function.api.layers, [])
      runtime_policy_actions = local.api_runtime_policy_actions
    }

    worker = {
      name                   = aws_lambda_function.worker.function_name
      runtime                = aws_lambda_function.worker.runtime
      architecture           = aws_lambda_function.worker.architectures[0]
      memory_mb              = aws_lambda_function.worker.memory_size
      timeout                = aws_lambda_function.worker.timeout
      log_group              = aws_cloudwatch_log_group.worker.name
      batch_size             = aws_lambda_event_source_mapping.worker_processing_queue.batch_size
      enabled                = aws_lambda_event_source_mapping.worker_processing_queue.enabled
      dependency_layer_count = length(coalesce(aws_lambda_function.worker.layers, []))
    }

    outbox_publisher = {
      name                   = aws_lambda_function.outbox_publisher.function_name
      runtime                = aws_lambda_function.outbox_publisher.runtime
      architecture           = aws_lambda_function.outbox_publisher.architectures[0]
      memory_mb              = aws_lambda_function.outbox_publisher.memory_size
      timeout                = aws_lambda_function.outbox_publisher.timeout
      log_group              = aws_cloudwatch_log_group.outbox_publisher.name
      schedule               = aws_cloudwatch_event_rule.outbox_publisher_schedule.name
      dependency_layer_count = length(coalesce(aws_lambda_function.outbox_publisher.layers, []))
    }
  }
}

output "resume_analysis_contract" {
  description = "Regional contract for the multi-Region Resume Analysis system of record."

  value = {
    table_name       = var.resume_analysis.table_name
    table_arn        = var.resume_analysis.table_arn
    consistency_mode = var.resume_analysis.consistency_mode
    witness_region   = var.resume_analysis.witness_region
  }
}

output "api_gateway" {
  value = {
    id            = aws_apigatewayv2_api.regional.id
    name          = aws_apigatewayv2_api.regional.name
    protocol_type = aws_apigatewayv2_api.regional.protocol_type
    endpoint      = aws_apigatewayv2_api.regional.api_endpoint
    execution_arn = aws_apigatewayv2_api.regional.execution_arn

    stage = {
      name        = aws_apigatewayv2_stage.default.name
      auto_deploy = aws_apigatewayv2_stage.default.auto_deploy
      log_group   = aws_cloudwatch_log_group.api_access.name

      throttling = {
        burst_limit = var.api.throttling_burst_limit
        rate_limit  = var.api.throttling_rate_limit
      }
    }

    authorizer = {
      name             = aws_apigatewayv2_authorizer.cognito.name
      type             = aws_apigatewayv2_authorizer.cognito.authorizer_type
      identity_sources = aws_apigatewayv2_authorizer.cognito.identity_sources
      issuer           = var.identity.issuer
      audience         = [var.identity.client_id]
    }

    routes = {
      public    = sort(tolist(local.public_api_routes))
      protected = sort(tolist(local.protected_api_routes))
    }
  }
}

output "observability" {
  value = {
    metric_namespace           = var.observability.metric_namespace
    structured_logging_enabled = var.observability.structured_logging_enabled
    active_tracing_enabled     = var.observability.active_tracing_enabled

    log_groups = {
      api              = aws_cloudwatch_log_group.api.name
      worker           = aws_cloudwatch_log_group.worker.name
      outbox_publisher = aws_cloudwatch_log_group.outbox_publisher.name
      api_access       = aws_cloudwatch_log_group.api_access.name
    }

    tracing_modes = {
      api              = aws_lambda_function.api.tracing_config[0].mode
      worker           = aws_lambda_function.worker.tracing_config[0].mode
      outbox_publisher = aws_lambda_function.outbox_publisher.tracing_config[0].mode
    }

    alarms = {
      enabled = var.observability.operational_alarms_enabled

      names = var.observability.operational_alarms_enabled ? sort(
        concat(
          [
            aws_cloudwatch_metric_alarm.api_5xx[0].alarm_name,
            aws_cloudwatch_metric_alarm.api_latency[0].alarm_name,
            aws_cloudwatch_metric_alarm.processing_queue_age[0].alarm_name,
            aws_cloudwatch_metric_alarm.processing_queue_depth[0].alarm_name,
            aws_cloudwatch_metric_alarm.processing_dlq_messages[0].alarm_name,
            aws_cloudwatch_metric_alarm.dynamodb_throttles[0].alarm_name,
            aws_cloudwatch_metric_alarm.worker_record_failures[0].alarm_name,
            aws_cloudwatch_metric_alarm.outbox_publish_failures[0].alarm_name,
          ],
          [
            for alarm in aws_cloudwatch_metric_alarm.lambda_errors :
            alarm.alarm_name
          ],
        )
      ) : []
    }
  }
}
