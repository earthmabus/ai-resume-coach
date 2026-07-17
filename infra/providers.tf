provider "aws" {
  alias  = "us_east_1"
  region = local.sites.east.region

  default_tags {
    tags = merge(
      local.common_tags,
      {
        Scope      = "regional"
        RegionRole = local.sites.east.role
        Site       = "east"
      },
    )
  }
}

provider "aws" {
  alias  = "us_west_2"
  region = local.sites.west.region

  default_tags {
    tags = merge(
      local.common_tags,
      {
        Scope      = "regional"
        RegionRole = local.sites.west.role
        Site       = "west"
      },
    )
  }
}

provider "aws" {
  alias  = "us_east_2"
  region = local.witness_region

  default_tags {
    tags = merge(
      local.common_tags,
      {
        Scope      = "multi-region-data"
        RegionRole = "witness"
        Site       = "witness"
      },
    )
  }
}
