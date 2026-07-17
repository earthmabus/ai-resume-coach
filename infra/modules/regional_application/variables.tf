variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "architecture_version" {
  type = string
}

variable "site_name" {
  type = string

  validation {
    condition     = contains(["east", "west"], var.site_name)
    error_message = "site_name must be east or west."
  }
}

variable "region" {
  type = string
}

variable "region_code" {
  type = string

  validation {
    condition     = can(regex("^[a-z0-9]{4}$", var.region_code))
    error_message = "region_code must contain exactly four lowercase letters or digits."
  }
}

variable "region_role" {
  type = string

  validation {
    condition     = contains(["active", "standby"], var.region_role)
    error_message = "region_role must be active or standby."
  }
}

variable "runtime" {
  type = object({
    app_version       = string
    deployment_id     = string
    log_level         = string
    analysis_provider = string
    openai_model      = string
  })
}

variable "common_tags" {
  type = map(string)
}

variable "identity" {
  description = "Shared identity configuration consumed by the regional API."
  type = object({
    user_pool_id = string
    client_id    = string
    issuer       = string
  })
}

variable "storage" {
  description = "Regional document-storage configuration."
  type = object({
    force_destroy                      = bool
    noncurrent_version_expiration_days = number
  })
}

variable "messaging" {
  description = "Regional asynchronous-processing configuration."
  type = object({
    visibility_timeout_seconds = number
    queue_retention_seconds    = number
    dlq_retention_seconds      = number
    max_receive_count          = number
    publisher_schedule         = string
  })
}

variable "packages" {
  description = "Deterministic Lambda package artifacts produced by the root module."
  type = object({
    api = object({
      filename         = string
      source_code_hash = string
    })
    worker = object({
      filename         = string
      source_code_hash = string
    })
    outbox_publisher = object({
      filename         = string
      source_code_hash = string
    })
  })
}

variable "compute" {
  description = "Regional Lambda runtime and event-source configuration."
  type = object({
    runtime                                = string
    architecture                           = string
    log_retention_days                     = number
    api_memory_mb                          = number
    api_timeout_seconds                    = number
    worker_memory_mb                       = number
    worker_timeout_seconds                 = number
    outbox_publisher_memory_mb             = number
    outbox_publisher_timeout_seconds       = number
    worker_batch_size                      = number
    worker_maximum_batching_window_seconds = number
  })
}

variable "data" {
  description = "Shared MRSC application-table contract for this regional application site."
  type = object({
    table_name         = string
    regional_table_arn = string
    consistency_mode   = string
    witness_region     = string
  })

  validation {
    condition     = var.data.consistency_mode == "STRONG"
    error_message = "Regional application sites require the MRSC application table."
  }
}

variable "api" {
  description = "Regional HTTP API configuration."
  type = object({
    cors_allowed_origins      = list(string)
    throttling_burst_limit    = number
    throttling_rate_limit     = number
    access_log_retention_days = number
  })
}

variable "observability" {
  description = "Regional telemetry, tracing, and alarm configuration."
  type = object({
    metric_namespace            = string
    structured_logging_enabled  = bool
    active_tracing_enabled      = bool
    operational_alarms_enabled  = bool
    alarm_actions               = list(string)
    api_5xx_threshold           = number
    api_latency_threshold_ms    = number
    lambda_error_threshold      = number
    queue_age_threshold_seconds = number
    queue_depth_threshold       = number
  })
}
