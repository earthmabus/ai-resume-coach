variable "project_name" {
  description = "Project name used in resource names and tags."
  type        = string
  default     = "ai-resume-coach"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"

  validation {
    condition = contains(
      ["dev", "test", "stage", "prod"],
      var.environment,
    )

    error_message = "environment must be dev, test, stage, or prod."
  }
}

variable "app_version" {
  description = "Application semantic version."
  type        = string
  default     = "0.1.0"
}

variable "deployment_id" {
  description = "Identifier for the deployed build, normally a Git commit SHA."
  type        = string
  default     = "local"
}

variable "log_level" {
  description = "Application logging level."
  type        = string
  default     = "INFO"

  validation {
    condition = contains(
      ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
      upper(var.log_level),
    )

    error_message = "log_level must be a supported Python logging level."
  }
}

variable "analysis_provider" {
  description = "Resume-analysis provider."
  type        = string
  default     = "rule-based"
}

variable "openai_model" {
  description = "OpenAI model used for analysis."
  type        = string
  default     = "gpt-5.5"
}

variable "openai_api_key" {
  description = "OpenAI API key."
  type        = string
  sensitive   = true
  default     = ""
}

variable "registration_notification_email" {
  description = "Email notified when a user registers."
  type        = string
  default     = ""
}

variable "operational_alert_email" {
  description = "Email for operational alarms."
  type        = string
  default     = ""
}

variable "frontend_domain_name" {
  description = "Custom frontend domain."
  type        = string
  default     = "resume.michaelpopovich.com"
}

variable "document_bucket_force_destroy" {
  description = "Allow Terraform to remove non-empty regional document buckets."
  type        = bool
  default     = false
}

variable "document_noncurrent_version_expiration_days" {
  description = "Days to retain noncurrent document versions."
  type        = number
  default     = 30

  validation {
    condition     = var.document_noncurrent_version_expiration_days >= 1
    error_message = "document_noncurrent_version_expiration_days must be at least 1."
  }
}

variable "processing_queue_visibility_timeout_seconds" {
  description = "Visibility timeout for regional processing queues."
  type        = number
  default     = 180

  validation {
    condition = (
      var.processing_queue_visibility_timeout_seconds >= 30
      && var.processing_queue_visibility_timeout_seconds <= 43200
    )
    error_message = "processing_queue_visibility_timeout_seconds must be between 30 and 43200."
  }
}

variable "processing_queue_message_retention_seconds" {
  description = "Retention period for regional processing queues."
  type        = number
  default     = 345600

  validation {
    condition = (
      var.processing_queue_message_retention_seconds >= 60
      && var.processing_queue_message_retention_seconds <= 1209600
    )
    error_message = "processing_queue_message_retention_seconds must be between 60 and 1209600."
  }
}

variable "processing_dlq_message_retention_seconds" {
  description = "Retention period for regional processing dead-letter queues."
  type        = number
  default     = 1209600

  validation {
    condition = (
      var.processing_dlq_message_retention_seconds >= 60
      && var.processing_dlq_message_retention_seconds <= 1209600
    )
    error_message = "processing_dlq_message_retention_seconds must be between 60 and 1209600."
  }
}

variable "processing_queue_max_receive_count" {
  description = "Receive attempts before a processing message moves to the DLQ."
  type        = number
  default     = 5

  validation {
    condition     = var.processing_queue_max_receive_count >= 1
    error_message = "processing_queue_max_receive_count must be at least 1."
  }
}

variable "outbox_publisher_schedule_expression" {
  description = "EventBridge schedule reserved for each regional outbox publisher."
  type        = string
  default     = "rate(1 minute)"
}

variable "enable_outbox_publisher_schedule" {
  description = "Enable regional EventBridge schedules that invoke the outbox publishers."
  type        = bool
  default     = false

  validation {
    condition = (
      !var.enable_outbox_publisher_schedule
      ||
      var.environment == "dev"
    )
    error_message = "Outbox publisher schedules can only be enabled in dev until a production activation decision exists."
  }
}

variable "lambda_runtime" {
  description = "Python runtime used by regional application functions."
  type        = string
  default     = "python3.13"
}

variable "lambda_architecture" {
  description = "Instruction-set architecture used by regional application functions."
  type        = string
  default     = "arm64"

  validation {
    condition     = contains(["arm64", "x86_64"], var.lambda_architecture)
    error_message = "lambda_architecture must be arm64 or x86_64."
  }
}

variable "lambda_log_retention_days" {
  description = "CloudWatch Logs retention for regional application functions."
  type        = number
  default     = 30

  validation {
    condition     = var.lambda_log_retention_days >= 1
    error_message = "lambda_log_retention_days must be at least 1."
  }
}

variable "api_lambda_memory_mb" {
  type    = number
  default = 512
}

variable "api_lambda_timeout_seconds" {
  type    = number
  default = 30
}

variable "worker_lambda_memory_mb" {
  type    = number
  default = 1024
}

variable "worker_lambda_timeout_seconds" {
  type    = number
  default = 120
}

variable "outbox_publisher_lambda_memory_mb" {
  type    = number
  default = 256
}

variable "outbox_publisher_lambda_timeout_seconds" {
  type    = number
  default = 30
}

variable "worker_batch_size" {
  description = "Maximum SQS records delivered to a worker invocation."
  type        = number
  default     = 5

  validation {
    condition     = var.worker_batch_size >= 1 && var.worker_batch_size <= 10
    error_message = "worker_batch_size must be between 1 and 10."
  }
}

variable "worker_maximum_batching_window_seconds" {
  description = "Maximum SQS batching window for worker invocations."
  type        = number
  default     = 5

  validation {
    condition = (
      var.worker_maximum_batching_window_seconds >= 0
      && var.worker_maximum_batching_window_seconds <= 300
    )
    error_message = "worker_maximum_batching_window_seconds must be between 0 and 300."
  }
}

variable "dynamodb_deletion_protection_enabled" {
  description = "Protect the MRSC application table from accidental deletion."
  type        = bool
  default     = false
}

variable "dynamodb_pitr_recovery_period_days" {
  description = "Continuous-backup recovery window for each application-table replica."
  type        = number
  default     = 35

  validation {
    condition = (
      var.dynamodb_pitr_recovery_period_days >= 1
      && var.dynamodb_pitr_recovery_period_days <= 35
    )
    error_message = "dynamodb_pitr_recovery_period_days must be between 1 and 35."
  }
}

variable "api_cors_allowed_origins" {
  description = "Origins allowed to call the regional HTTP APIs."
  type        = list(string)
  default = [
    "http://localhost:5173",
    "http://localhost:8000",
  ]

  validation {
    condition     = length(var.api_cors_allowed_origins) > 0
    error_message = "At least one CORS origin must be configured."
  }
}

variable "api_throttling_burst_limit" {
  description = "Default HTTP API burst limit per regional stage."
  type        = number
  default     = 25

  validation {
    condition     = var.api_throttling_burst_limit >= 1
    error_message = "api_throttling_burst_limit must be at least 1."
  }
}

variable "api_throttling_rate_limit" {
  description = "Default sustained HTTP API request rate per second."
  type        = number
  default     = 10

  validation {
    condition     = var.api_throttling_rate_limit > 0
    error_message = "api_throttling_rate_limit must be greater than zero."
  }
}

variable "api_access_log_retention_days" {
  description = "CloudWatch retention for regional HTTP API access logs."
  type        = number
  default     = 14

  validation {
    condition     = var.api_access_log_retention_days >= 1
    error_message = "api_access_log_retention_days must be at least 1."
  }
}

variable "enable_global_api_routing" {
  description = "Create Regional API custom domains and Route 53 latency records."
  type        = bool
  default     = false
}



variable "site_routing_enabled" {
  description = "Controls whether each active site is published in global Route 53 routing."
  type = object({
    east = bool
    west = bool
  })
  default = {
    east = true
    west = true
  }

  validation {
    condition     = var.site_routing_enabled.east || var.site_routing_enabled.west
    error_message = "At least one regional site must remain enabled for routing."
  }
}

variable "production_readiness_enforced" {
  description = "Require the minimum routing, security, and observability controls before deployment."
  type        = bool
  default     = false
}

variable "enable_route53_api_health_checks" {
  description = "Create paid Route 53 endpoint health checks and associate them with latency records."
  type        = bool
  default     = false

  validation {
    condition = (
      !var.enable_route53_api_health_checks
      ||
      var.enable_global_api_routing
    )
    error_message = "Route 53 API health checks require global API routing to be enabled."
  }
}

variable "api_domain_name" {
  description = "Shared API hostname used by both Regional API Gateway custom domains."
  type        = string
  default     = "api.resume.michaelpopovich.com"
}

variable "route53_public_zone_id" {
  description = "Existing Route 53 public hosted-zone ID that contains api_domain_name."
  type        = string
  default     = ""
}

variable "east_api_certificate_arn" {
  description = "Validated ACM certificate ARN in us-east-1 for api_domain_name."
  type        = string
  default     = ""
}

variable "west_api_certificate_arn" {
  description = "Validated ACM certificate ARN in us-west-2 for api_domain_name."
  type        = string
  default     = ""
}

variable "route53_health_check_failure_threshold" {
  description = "Consecutive failed Route 53 probes before an API endpoint is unhealthy."
  type        = number
  default     = 3

  validation {
    condition     = contains([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], var.route53_health_check_failure_threshold)
    error_message = "route53_health_check_failure_threshold must be between 1 and 10."
  }
}

variable "enable_cognito_waf" {
  description = "Create and associate an AWS WAF web ACL with the shared Cognito user pool."
  type        = bool
  default     = false
}

variable "enable_cognito_waf_logging" {
  description = "Send Cognito WAF logs to a short-retention CloudWatch Logs group."
  type        = bool
  default     = false

  validation {
    condition = (
      !var.enable_cognito_waf_logging
      ||
      var.enable_cognito_waf
    )
    error_message = "Cognito WAF logging requires Cognito WAF protection to be enabled."
  }
}

variable "enable_synthetic_placement_override" {
  description = "Enable the authenticated development-only owner-region override for runtime validation."
  type        = bool
  default     = false

  validation {
    condition = (
      !var.enable_synthetic_placement_override
      ||
      var.environment == "dev"
    )
    error_message = "Synthetic placement override can only be enabled in dev."
  }
}

variable "synthetic_placement_override_group_name" {
  description = "Cognito group authorized to request synthetic owner-region placement in development."
  type        = string
  default     = "synthetic-runtime-validation"

  validation {
    condition     = length(trimspace(var.synthetic_placement_override_group_name)) > 0
    error_message = "synthetic_placement_override_group_name must not be blank."
  }
}

variable "cognito_waf_rate_limit" {
  description = "Maximum requests allowed from one source IP in the AWS WAF five-minute evaluation window."
  type        = number
  default     = 500

  validation {
    condition     = var.cognito_waf_rate_limit >= 100 && var.cognito_waf_rate_limit <= 2000000000
    error_message = "cognito_waf_rate_limit must be between 100 and 2,000,000,000."
  }
}

variable "cognito_waf_log_retention_days" {
  description = "CloudWatch retention for optional WAF logs."
  type        = number
  default     = 7

  validation {
    condition = contains(
      [1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365],
      var.cognito_waf_log_retention_days,
    )
    error_message = "cognito_waf_log_retention_days must be a supported CloudWatch Logs retention value."
  }
}

variable "telemetry_metric_namespace" {
  description = "Root CloudWatch namespace for platform and business custom metrics."
  type        = string
  default     = "AIResumeCoach/Platform"

  validation {
    condition     = can(regex("^[A-Za-z0-9._/#-]{1,255}$", var.telemetry_metric_namespace))
    error_message = "telemetry_metric_namespace must be a valid CloudWatch namespace."
  }
}

variable "enable_structured_logging" {
  description = "Expose and inject the Platform V2 structured-JSON logging contract."
  type        = bool
  default     = true
}

variable "enable_active_tracing" {
  description = "Enable AWS X-Ray active tracing for the regional Lambda functions."
  type        = bool
  default     = false
}

variable "enable_observability_dashboard" {
  description = "Create the shared CloudWatch operations dashboard."
  type        = bool
  default     = false
}

variable "enable_operational_alarms" {
  description = "Create the curated regional CloudWatch alarm set."
  type        = bool
  default     = false
}

variable "observability_alarm_actions" {
  description = "Optional SNS topic ARNs or other actions used by operational alarms."
  type        = list(string)
  default     = []
}

variable "api_5xx_alarm_threshold" {
  description = "API Gateway 5XX count threshold over the alarm evaluation window."
  type        = number
  default     = 5

  validation {
    condition     = var.api_5xx_alarm_threshold >= 1
    error_message = "api_5xx_alarm_threshold must be at least 1."
  }
}

variable "api_latency_alarm_threshold_ms" {
  description = "Regional HTTP API p95 latency alarm threshold in milliseconds."
  type        = number
  default     = 3000

  validation {
    condition     = var.api_latency_alarm_threshold_ms >= 100
    error_message = "api_latency_alarm_threshold_ms must be at least 100."
  }
}

variable "lambda_error_alarm_threshold" {
  description = "Lambda error count threshold over the alarm evaluation window."
  type        = number
  default     = 3

  validation {
    condition     = var.lambda_error_alarm_threshold >= 1
    error_message = "lambda_error_alarm_threshold must be at least 1."
  }
}

variable "queue_age_alarm_threshold_seconds" {
  description = "Maximum acceptable age of the oldest processing-queue message."
  type        = number
  default     = 300

  validation {
    condition     = var.queue_age_alarm_threshold_seconds >= 60
    error_message = "queue_age_alarm_threshold_seconds must be at least 60."
  }
}

variable "queue_depth_alarm_threshold" {
  description = "Maximum acceptable visible processing-queue depth."
  type        = number
  default     = 25

  validation {
    condition     = var.queue_depth_alarm_threshold >= 1
    error_message = "queue_depth_alarm_threshold must be at least 1."
  }
}

variable "enable_synthetic_monitoring" {
  description = "Create one CloudWatch Synthetics health canary in each active Region."
  type        = bool
  default     = false
}

variable "synthetic_schedule_expression" {
  description = "CloudWatch Synthetics schedule. Five minutes is the cost-conscious default."
  type        = string
  default     = "rate(5 minutes)"
}

variable "synthetic_runtime_version" {
  description = "Supported CloudWatch Synthetics Node.js runtime."
  type        = string
  default     = "syn-nodejs-5.1"
}

variable "synthetic_artifact_retention_days" {
  description = "Retention for versioned Synthetics artifacts in regional S3 buckets."
  type        = number
  default     = 7

  validation {
    condition     = var.synthetic_artifact_retention_days >= 1
    error_message = "synthetic_artifact_retention_days must be at least 1."
  }
}

variable "synthetic_timeout_seconds" {
  description = "Maximum duration for one regional health-canary run."
  type        = number
  default     = 60

  validation {
    condition     = var.synthetic_timeout_seconds >= 3 && var.synthetic_timeout_seconds <= 900
    error_message = "synthetic_timeout_seconds must be between 3 and 900."
  }
}
