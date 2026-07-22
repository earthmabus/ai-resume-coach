module "shared_foundation" {
  source = "./modules/shared_foundation"

  providers = {
    aws = aws.us_east_1
  }

  project_name         = var.project_name
  environment          = var.environment
  architecture_version = local.architecture_version
  common_tags          = local.common_tags

  east_region    = local.sites.east.region
  west_region    = local.sites.west.region
  witness_region = local.witness_region

  registration_notification_email = var.registration_notification_email
  registration_notification_package = {
    filename         = data.archive_file.registration_notification_zip.output_path
    source_code_hash = data.archive_file.registration_notification_zip.output_base64sha256
  }

  runtime = {
    app_version   = var.app_version
    deployment_id = var.deployment_id
    log_level     = var.log_level
  }

  enable_synthetic_placement_override     = var.enable_synthetic_placement_override
  synthetic_placement_override_group_name = var.synthetic_placement_override_group_name
  dynamodb_deletion_protection_enabled    = var.dynamodb_deletion_protection_enabled
  dynamodb_pitr_recovery_period_days      = var.dynamodb_pitr_recovery_period_days
}

locals {
  resume_analysis_table      = module.shared_foundation.resume_analysis
  resume_analysis_table_arns = module.shared_foundation.resume_analysis_table_arns
}
