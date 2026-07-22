variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "architecture_version" {
  type = string
}

variable "common_tags" {
  type = map(string)
}

variable "east_region" {
  type = string
}

variable "west_region" {
  type = string
}

variable "witness_region" {
  type = string
}

variable "registration_notification_email" {
  type = string
}

variable "registration_notification_package" {
  type = object({
    filename         = string
    source_code_hash = string
  })
}

variable "runtime" {
  type = object({
    app_version   = string
    deployment_id = string
    log_level     = string
  })
}

variable "enable_synthetic_placement_override" {
  type = bool
}

variable "synthetic_placement_override_group_name" {
  type = string
}

variable "dynamodb_deletion_protection_enabled" {
  type = bool
}

variable "dynamodb_pitr_recovery_period_days" {
  type = number
}
