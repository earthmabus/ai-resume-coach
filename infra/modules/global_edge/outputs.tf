output "domain_name" {
  value = var.domain_name
}

output "primary_site" {
  value = var.primary_site
}

output "identity" {
  value = local.identity
}

output "global_api" {
  value = {
    enabled               = var.global_api.enabled
    health_checks_enabled = var.global_api.health_checks_enabled
    domain_name           = var.global_api.domain_name
    routing_policy        = "LATENCY"
    active_regions = compact([
      var.global_api.routing_enabled.east ? var.primary_site.region : "",
      var.global_api.routing_enabled.west ? var.secondary_site.region : "",
    ])
    routing_enabled = var.global_api.routing_enabled
    health_path     = "/health/ready"
    tls_policy      = "TLS_1_2"
  }
}
