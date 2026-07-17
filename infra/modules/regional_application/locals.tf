locals {
  name_prefix = join(
    "-",
    [
      var.project_name,
      var.environment,
      var.region_code,
    ],
  )

  site_identity = {
    name                = var.site_name
    region              = var.region
    regionCode          = var.region_code
    role                = var.region_role
    architectureVersion = var.architecture_version
    resourceNamePrefix  = local.name_prefix
    deploymentId        = var.runtime.deployment_id
    applicationVersion  = var.runtime.app_version
  }

  tags = merge(
    var.common_tags,
    {
      Site       = var.site_name
      RegionCode = var.region_code
      RegionRole = var.region_role
    },
  )
}
