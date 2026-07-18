mock_provider "aws" {
  alias = "us_east_1"
}

mock_provider "aws" {
  alias = "us_west_2"
}

mock_provider "aws" {
  alias = "us_east_2"
}

mock_provider "archive" {}

run "telemetry_contract_is_structured_and_privacy_aware" {
  command = plan

  assert {
    condition = (
      output.observability.telemetry.structured_logging_enabled
      &&
      output.observability.telemetry.metric_namespace == "AIResumeCoach/Platform"
      &&
      output.observability.telemetry.schema_version == "1.0"
    )
    error_message = "Platform telemetry must use the approved structured logging and metric namespace contract."
  }

  assert {
    condition = (
      contains(output.observability.telemetry.schema_fields, "requestId")
      &&
      contains(output.observability.telemetry.schema_fields, "correlationId")
      &&
      contains(output.observability.telemetry.schema_fields, "deploymentId")
      &&
      contains(output.observability.telemetry.schema_fields, "architectureVersion")
    )
    error_message = "The telemetry schema must include request, workflow, deployment, and architecture correlation fields."
  }

  assert {
    condition = (
      output.observability.telemetry.correlation_model.propagation_header == "x-correlation-id"
      &&
      contains(output.observability.telemetry.privacy.never_logged_fields, "authorization")
      &&
      contains(output.observability.telemetry.privacy.never_logged_fields, "password")
      &&
      contains(output.observability.telemetry.privacy.never_logged_fields, "resumeText")
    )
    error_message = "The telemetry contract must define correlation propagation and prohibit secrets and resume content in logs."
  }
}

run "paid_observability_features_are_cost_gated_by_default" {
  command = plan

  assert {
    condition = (
      output.observability.tracing.enabled == false
      &&
      output.observability.dashboard.enabled == false
      &&
      output.observability.alarms.enabled == false
      &&
      output.observability.synthetics.enabled == false
    )
    error_message = "Tracing, dashboards, alarms, and synthetics must remain explicitly cost-gated."
  }

  assert {
    condition = (
      output.observability.telemetry.retention_days.application > 0
      &&
      output.observability.telemetry.retention_days.api_access > 0
      &&
      output.observability.telemetry.retention_days.waf > 0
      &&
      output.observability.telemetry.retention_days.synthetic_artifacts > 0
    )
    error_message = "Every retained telemetry class must expose a positive retention period."
  }
}

run "active_tracing_is_symmetric_when_enabled" {
  command = plan

  variables {
    enable_active_tracing = true
  }

  assert {
    condition = (
      output.observability.tracing.enabled
      &&
      output.observability.tracing.east_modes.api == "Active"
      &&
      output.observability.tracing.east_modes.worker == "Active"
      &&
      output.observability.tracing.east_modes.outbox_publisher == "Active"
      &&
      output.observability.tracing.west_modes.api == "Active"
      &&
      output.observability.tracing.west_modes.worker == "Active"
      &&
      output.observability.tracing.west_modes.outbox_publisher == "Active"
    )
    error_message = "Active tracing must be applied symmetrically to every regional Lambda role."
  }

  assert {
    condition = (
      output.observability.tracing.provider == "AWS_XRAY"
      &&
      output.observability.tracing.api_gateway_http_api_active_tracing_supported == false
    )
    error_message = "The tracing contract must accurately document Lambda X-Ray and the HTTP API limitation."
  }
}

run "dashboard_and_alarm_contracts_cover_both_regions" {
  command = plan

  variables {
    enable_observability_dashboard = true
    enable_operational_alarms      = true
  }

  assert {
    condition = (
      output.observability.dashboard.enabled
      &&
      length(output.observability.dashboard.regional_sites) == 2
      &&
      contains(output.observability.dashboard.regional_sites, "east")
      &&
      contains(output.observability.dashboard.regional_sites, "west")
      &&
      output.observability.dashboard.includes_business_metric_namespace
      &&
      output.observability.dashboard.includes_worker_outbox_failures
      &&
      output.observability.dashboard.includes_lambda_throttles
      &&
      output.observability.dashboard.includes_dlq_depth
    )
    error_message = "The operations dashboard must represent both active sites, reserve the business metric namespace, and expose key failure, throttle, and DLQ signals."
  }

  assert {
    condition = (
      output.observability.alarms.enabled
      &&
      length(output.observability.alarms.names) == 22
      &&
      contains(output.observability.alarms.categories, "API_AVAILABILITY")
      &&
      contains(output.observability.alarms.categories, "DLQ")
      &&
      contains(output.observability.alarms.categories, "DYNAMODB_THROTTLING")
      &&
      contains(output.observability.alarms.categories, "WORKER_RECORD_FAILURES")
      &&
      contains(output.observability.alarms.categories, "OUTBOX_PUBLISH_FAILURES")
    )
    error_message = "The curated alarm set must contain eleven alarms per active Region and cover the approved operational categories."
  }

  assert {
    condition = (
      output.observability.alarms.missing_data_treatment.native_error_and_backlog_metrics == "notBreaching"
      &&
      output.observability.alarms.missing_data_treatment.application_failure_metrics == "notBreaching"
      &&
      contains(output.observability.alarms.bounded_dimensions, "FunctionName")
      &&
      !contains(output.observability.alarms.bounded_dimensions, "requestId")
      &&
      !contains(output.observability.alarms.bounded_dimensions, "correlationId")
      &&
      !contains(output.observability.alarms.bounded_dimensions, "outboxEventId")
    )
    error_message = "Operational alarms must document intentional missing-data handling and avoid high-cardinality dimensions."
  }
}

run "synthetic_monitoring_checks_all_public_health_contracts" {
  command = plan

  variables {
    enable_synthetic_monitoring = true
  }

  assert {
    condition = (
      output.observability.synthetics.enabled
      &&
      output.observability.synthetics.schedule_expression == "rate(5 minutes)"
      &&
      output.observability.synthetics.artifact_retention_days == 7
    )
    error_message = "Synthetic monitoring must use the cost-conscious schedule and short artifact retention."
  }

  assert {
    condition = (
      length(output.observability.synthetics.health_paths) == 3
      &&
      contains(output.observability.synthetics.health_paths, "/health")
      &&
      contains(output.observability.synthetics.health_paths, "/health/live")
      &&
      contains(output.observability.synthetics.health_paths, "/health/ready")
      &&
      length(output.observability.synthetics.regional_canaries) == 2
    )
    error_message = "Each active Region must receive a synthetic canary that checks every public health endpoint."
  }
}
