variable "aws_region" {
  description = "AWS region for the project."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for resource naming."
  type        = string
  default     = "ai-resume-coach"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"
}

variable "analysis_provider" {
  description = "Resume analysis provider to use."
  type        = string
  default     = "rule-based"
}

variable "openai_model" {
  description = "OpenAI model used for resume analysis."
  type        = string
  default     = "gpt-5.5"
}

variable "openai_api_key" {
  description = "OpenAI API key for AI resume analysis."
  type        = string
  sensitive   = true
  default     = ""
}

variable "registration_notification_email" {
  description = "Email address to notify when a new user registers"
  type        = string
}

variable "app_version" {
  description = "Application semantic version exposed by the version endpoint."
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
      upper(var.log_level)
    )

    error_message = "log_level must be a supported Python logging level."
  }
}
