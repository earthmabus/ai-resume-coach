output "architecture_version" {
  description = "Infrastructure architecture version."
  value       = local.architecture_version
}

output "regional_sites" {
  description = "Regional site identities."

  value = {
    east = module.east.site_identity
    west = module.west.site_identity
  }
}

output "east_region" {
  description = "East active application Region."
  value       = module.east.region
}

output "west_region" {
  description = "West active application Region."
  value       = module.west.region
}

output "witness_region" {
  description = "DynamoDB MRSC witness Region."
  value       = local.witness_region
}

output "frontend_domain_name" {
  description = "Configured frontend domain."
  value       = module.global_edge.domain_name
}

output "frontend_url" {
  description = "Public HTTPS URL for the static frontend."
  value       = var.enable_frontend_hosting ? "https://${var.frontend_domain_name}" : null
}

output "frontend_bucket_name" {
  description = "Private S3 bucket receiving frontend deployment artifacts."
  value       = var.enable_frontend_hosting ? aws_s3_bucket.frontend[0].id : null
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID used for frontend cache invalidations."
  value       = var.enable_frontend_hosting ? aws_cloudfront_distribution.frontend[0].id : null
}

output "cloudfront_distribution_domain_name" {
  description = "CloudFront-generated domain name for the frontend distribution."
  value       = var.enable_frontend_hosting ? aws_cloudfront_distribution.frontend[0].domain_name : null
}

output "primary_frontend_site" {
  description = "Regional site selected as the initial frontend API target."
  value       = module.global_edge.primary_site
}

output "cognito_user_pool_id" {
  description = "Shared Cognito user-pool ID."
  value       = module.shared_foundation.identity.user_pool_id
}

output "cognito_user_pool_client_id" {
  description = "Shared Cognito web-client ID."
  value       = module.shared_foundation.identity.client_id
}

output "cognito_user_pool_domain" {
  description = "Shared Cognito hosted-domain prefix."
  value       = module.shared_foundation.identity.domain
}

output "cognito_issuer" {
  description = "JWT issuer trusted by both regional APIs."

  value = module.shared_foundation.identity.issuer
}

output "registration_notification_lambda_name" {
  description = "Shared registration-notification Lambda function name."
  value       = module.shared_foundation.registration_notification.lambda_name
}

output "registration_notification_topic_arn" {
  description = "SNS topic receiving registration notifications."
  value       = module.shared_foundation.registration_notification.topic_arn
}

output "lambda_package_hashes" {
  description = "Deterministic hashes for isolated Lambda packages."

  value = {
    api                       = data.archive_file.api_zip.output_base64sha256
    worker                    = data.archive_file.worker_zip.output_base64sha256
    outbox_publisher          = data.archive_file.outbox_publisher_zip.output_base64sha256
    registration_notification = data.archive_file.registration_notification_zip.output_base64sha256
    pdf_dependency_layer      = data.archive_file.pdf_dependency_layer_zip.output_base64sha256
  }
}

output "regional_foundations" {
  description = "Regional storage, messaging, scheduling, compute, data, and API foundations."

  value = {
    east = {
      document_bucket           = module.east.document_bucket
      processing_queue          = module.east.processing_queue
      processing_dlq            = module.east.processing_dlq
      terminal_failure_dlq      = module.east.terminal_failure_dlq
      outbox_publisher_schedule = module.east.outbox_publisher_schedule
      execution_roles           = module.east.execution_roles
      compute                   = module.east.compute
      routing                   = module.east.routing
      regional_transport        = module.east.regional_transport
      resume_analysis           = module.east.resume_analysis_contract
      api_gateway               = module.east.api_gateway
      validation                = module.east.validation
    }

    west = {
      document_bucket           = module.west.document_bucket
      processing_queue          = module.west.processing_queue
      processing_dlq            = module.west.processing_dlq
      terminal_failure_dlq      = module.west.terminal_failure_dlq
      outbox_publisher_schedule = module.west.outbox_publisher_schedule
      execution_roles           = module.west.execution_roles
      compute                   = module.west.compute
      routing                   = module.west.routing
      regional_transport        = module.west.regional_transport
      resume_analysis           = module.west.resume_analysis_contract
      api_gateway               = module.west.api_gateway
      validation                = module.west.validation
    }
  }
}

output "resume_analysis_data" {
  description = "DynamoDB MRSC Resume Analysis system-of-record contract."

  value = {
    table_name         = module.shared_foundation.resume_analysis.name
    primary_table_arn  = module.shared_foundation.resume_analysis.primary_arn
    primary_region     = local.resume_analysis_table.primary_region
    replica_regions    = local.resume_analysis_table.replica_regions
    witness_region     = local.resume_analysis_table.witness_region
    consistency_mode   = local.resume_analysis_table.consistency_mode
    billing_mode       = module.shared_foundation.resume_analysis.billing_mode
    pitr_enabled       = true
    deletion_protected = var.dynamodb_deletion_protection_enabled
    global_secondary_indexes = {
      gsi1 = {
        name            = "gsi1"
        hash_key        = "gsi1pk"
        range_key       = "gsi1sk"
        projection_type = "ALL"
      }

      gsi2 = {
        name            = "gsi2"
        hash_key        = "gsi2pk"
        range_key       = "gsi2sk"
        projection_type = "ALL"
      }
    }
  }
}

output "regional_api_endpoints" {
  description = "Direct regional HTTP API endpoints for validation before global routing."

  value = {
    east = module.east.api_gateway.endpoint
    west = module.west.api_gateway.endpoint
  }
}

output "global_api_routing" {
  description = "Feature-gated Route 53 latency-routing contract for the regional APIs."
  value       = module.global_edge.global_api
}

output "edge_security" {
  description = "Cost-gated edge-security and HTTP API hardening contract."

  value = {
    cognito_waf = {
      enabled             = var.enable_cognito_waf
      logging_enabled     = var.enable_cognito_waf_logging
      scope               = "REGIONAL"
      protected_resource  = "COGNITO_USER_POOL"
      rate_limit          = var.cognito_waf_rate_limit
      managed_rule_groups = local.cognito_waf_managed_rule_groups
      log_retention_days  = var.cognito_waf_log_retention_days
      redacted_headers    = ["authorization"]
    }

    regional_http_apis = {
      waf_association_supported = false
      protection_model          = "JWT_AUTHORIZATION_PLUS_STAGE_THROTTLING"
      east_throttling           = module.east.api_gateway.stage.throttling
      west_throttling           = module.west.api_gateway.stage.throttling
    }

    ddos_baseline = "AWS_SHIELD_STANDARD"
  }
}

output "observability" {
  description = "Platform V2 telemetry, dashboard, alarm, tracing, and synthetic-monitoring contract."

  value = {
    telemetry = {
      metric_namespace           = var.telemetry_metric_namespace
      structured_logging_enabled = var.enable_structured_logging
      schema_version             = "1.0"
      schema_fields              = local.telemetry_log_schema_fields

      correlation_model = {
        request_id_field     = "requestId"
        correlation_id_field = "correlationId"
        propagation_header   = "x-correlation-id"
        deployment_id_field  = "deploymentId"
      }

      privacy = {
        never_logged_fields           = local.telemetry_never_logged_fields
        authorization_header_redacted = true
      }

      retention_days = {
        application         = var.lambda_log_retention_days
        api_access          = var.api_access_log_retention_days
        waf                 = var.cognito_waf_log_retention_days
        synthetic_artifacts = var.synthetic_artifact_retention_days
      }
    }

    tracing = {
      enabled                                       = var.enable_active_tracing
      provider                                      = "AWS_XRAY"
      east_modes                                    = module.east.observability.tracing_modes
      west_modes                                    = module.west.observability.tracing_modes
      api_gateway_http_api_active_tracing_supported = false
    }

    dashboard = {
      enabled                            = var.enable_observability_dashboard
      name                               = local.observability_dashboard_name
      regional_sites                     = ["east", "west"]
      includes_business_metric_namespace = true
      includes_worker_outbox_failures    = true
      includes_lambda_throttles          = true
      includes_dlq_depth                 = true
      includes_regional_error_logs       = true
      includes_api_client_errors         = true
      includes_lambda_activity           = true
      includes_async_throughput          = true
      includes_dynamodb_capacity         = true
    }

    alarms = {
      enabled = var.enable_operational_alarms
      actions = var.observability_alarm_actions
      names   = local.regional_alarm_names

      categories = [
        "API_AVAILABILITY",
        "API_LATENCY",
        "LAMBDA_ERRORS",
        "QUEUE_AGE",
        "QUEUE_DEPTH",
        "DLQ",
        "DYNAMODB_THROTTLING",
        "WORKER_RECORD_FAILURES",
        "OUTBOX_PUBLISH_FAILURES",
      ]

      missing_data_treatment = {
        native_error_and_backlog_metrics = "notBreaching"
        application_failure_metrics      = "notBreaching"
      }

      bounded_dimensions = [
        "ApiId",
        "Stage",
        "FunctionName",
        "QueueName",
        "TableName",
      ]
    }

    synthetics = {
      enabled                 = var.enable_synthetic_monitoring
      schedule_expression     = var.synthetic_schedule_expression
      runtime_version         = var.synthetic_runtime_version
      health_paths            = ["/health", "/health/live", "/health/ready"]
      artifact_retention_days = var.synthetic_artifact_retention_days

      regional_canaries = var.enable_synthetic_monitoring ? {
        east = aws_synthetics_canary.east[0].name
        west = aws_synthetics_canary.west[0].name
      } : {}
    }

    log_groups = {
      east = module.east.observability.log_groups
      west = module.west.observability.log_groups
    }
  }
}

output "operations" {
  description = "Multi-site deployment, routing isolation, rollback, and production-readiness contract."

  value = {
    production_readiness_enforced = var.production_readiness_enforced
    production_ready              = local.production_ready
    required_production_controls  = local.required_production_controls
    missing_production_controls   = local.missing_production_controls

    routing_enabled_by_site = var.site_routing_enabled
    active_sites            = local.active_routing_sites

    deployment = {
      order = [
        "west",
        "validate-west",
        "east",
        "validate-east",
        "enable-global-routing",
      ]

      strategy = "REGIONAL_SEQUENTIAL"

      validation_contract = [
        "regional-health",
        "synthetics",
        "alarms",
        "deployment-id",
      ]
    }

    regional_health_endpoints = local.regional_health_endpoints

    rollback = {
      unit           = "REGIONAL_SITE"
      application    = "redeploy-previous-lambda-package"
      infrastructure = "apply-previous-validated-terraform-configuration"
      routing        = "disable-affected-site-route53-record"
      data           = "compensating-action-not-infrastructure-rollback"
    }
  }
}
