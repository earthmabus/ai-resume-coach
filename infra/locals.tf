locals {
  architecture_version = "platform-v2"

  sites = {
    east = {
      region      = "us-east-1"
      region_code = "use1"
      role        = "active"
    }

    west = {
      region      = "us-west-2"
      region_code = "usw2"
      role        = "active"
    }
  }

  witness_region = "us-east-2"

  global_name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project             = var.project_name
    Environment         = var.environment
    ManagedBy           = "Terraform"
    ArchitectureVersion = local.architecture_version
    Repository          = "earthmabus/ai-resume-coach"
  }

  application_runtime = {
    app_version       = var.app_version
    deployment_id     = var.deployment_id
    log_level         = upper(var.log_level)
    analysis_provider = var.analysis_provider
    openai_model      = var.openai_model
  }
}
