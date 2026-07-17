locals {
  name_prefix = "${var.project_name}-${var.environment}"

  identity = {
    domainName          = var.domain_name
    architectureVersion = var.architecture_version
    resourceNamePrefix  = local.name_prefix
  }

  tags = merge(
    var.common_tags,
    {
      Scope      = "global"
      RegionRole = "shared"
    },
  )
}
