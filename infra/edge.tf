module "global_edge" {
  source = "./modules/global_edge"

  providers = {
    aws.us_east_1 = aws.us_east_1
    aws.us_west_2 = aws.us_west_2
  }

  project_name         = var.project_name
  environment          = var.environment
  architecture_version = local.architecture_version
  domain_name          = var.frontend_domain_name

  primary_site = {
    name         = module.east.site_name
    region       = module.east.region
    region_code  = module.east.region_code
    api_endpoint = module.east.api_gateway.endpoint
    api_id       = module.east.api_gateway.id
  }

  secondary_site = {
    name         = module.west.site_name
    region       = module.west.region
    region_code  = module.west.region_code
    api_endpoint = module.west.api_gateway.endpoint
    api_id       = module.west.api_gateway.id
  }

  global_api = {
    enabled                  = var.enable_global_api_routing
    health_checks_enabled    = var.enable_route53_api_health_checks
    domain_name              = var.api_domain_name
    hosted_zone_id           = var.route53_public_zone_id
    east_certificate_arn     = var.east_api_certificate_arn
    west_certificate_arn     = var.west_api_certificate_arn
    health_failure_threshold = var.route53_health_check_failure_threshold
    routing_enabled          = var.site_routing_enabled
  }

  common_tags = merge(
    local.common_tags,
    {
      Scope      = "global"
      RegionRole = "shared"
    },
  )
}
