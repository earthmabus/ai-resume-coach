locals {
  required_production_controls = {
    global_api_routing      = var.enable_global_api_routing
    route53_health_checks   = var.enable_route53_api_health_checks
    cognito_waf             = var.enable_cognito_waf
    structured_logging      = var.enable_structured_logging
    observability_dashboard = var.enable_observability_dashboard
    operational_alarms      = var.enable_operational_alarms
    synthetic_monitoring    = var.enable_synthetic_monitoring
  }

  missing_production_controls = sort([
    for name, enabled in local.required_production_controls : name
    if !enabled
  ])

  production_ready = length(local.missing_production_controls) == 0

  active_routing_sites = compact([
    var.site_routing_enabled.east ? "east" : "",
    var.site_routing_enabled.west ? "west" : "",
  ])

  regional_health_endpoints = {
    east = "${module.east.api_gateway.endpoint}/health/ready"
    west = "${module.west.api_gateway.endpoint}/health/ready"
  }
}

resource "terraform_data" "production_readiness" {
  input = {
    enforced = var.production_readiness_enforced
    ready    = local.production_ready
  }

  lifecycle {
    precondition {
      condition = (
        !var.production_readiness_enforced
        || local.production_ready
      )
      error_message = "Production readiness enforcement failed. Enable all required production controls before deployment."
    }
  }
}
