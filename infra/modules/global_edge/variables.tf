variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "architecture_version" {
  type = string
}

variable "domain_name" {
  description = "Frontend domain retained for the global-edge contract."
  type        = string
}

variable "primary_site" {
  type = object({
    name         = string
    region       = string
    region_code  = string
    api_endpoint = string
    api_id       = string
  })
  nullable = true
}

variable "secondary_site" {
  type = object({
    name         = string
    region       = string
    region_code  = string
    api_endpoint = string
    api_id       = string
  })
  nullable = true
}

variable "global_api" {
  description = "Feature-gated global active-active API routing configuration."
  type = object({
    enabled                  = bool
    health_checks_enabled    = bool
    domain_name              = string
    hosted_zone_id           = string
    east_certificate_arn     = string
    west_certificate_arn     = string
    health_failure_threshold = number
    routing_enabled = object({
      east = bool
      west = bool
    })
  })

  validation {
    condition = (
      !var.global_api.enabled
      ||
      (
        trimspace(var.global_api.domain_name) != ""
        &&
        trimspace(var.global_api.hosted_zone_id) != ""
        &&
        trimspace(var.global_api.east_certificate_arn) != ""
        &&
        trimspace(var.global_api.west_certificate_arn) != ""
      )
    )
    error_message = "Enabled global API routing requires a domain, hosted-zone ID, and one validated certificate ARN per active Region."
  }
}

variable "common_tags" {
  type = map(string)
}
