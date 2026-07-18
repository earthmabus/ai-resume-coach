resource "aws_dynamodb_table" "resume_analysis" {
  provider = aws.us_east_1

  name         = "${local.global_name_prefix}-resume-analysis"
  billing_mode = "PAY_PER_REQUEST"
  table_class  = "STANDARD"

  deletion_protection_enabled = var.dynamodb_deletion_protection_enabled

  hash_key  = "pk"
  range_key = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  point_in_time_recovery {
    enabled                 = true
    recovery_period_in_days = var.dynamodb_pitr_recovery_period_days
  }

  server_side_encryption {
    enabled = true
  }

  replica {
    region_name            = local.sites.west.region
    consistency_mode       = "STRONG"
    point_in_time_recovery = true
    propagate_tags         = true
  }

  global_table_witness {
    region_name = local.witness_region
  }

  tags = merge(
    local.common_tags,
    {
      Scope          = "multi-region-data"
      Capability     = "resume-analysis-system-of-record"
      Consistency    = "multi-region-strong"
      PrimaryReplica = local.sites.east.region
      PeerReplica    = local.sites.west.region
      WitnessRegion  = local.witness_region
    },
  )
}

locals {
  resume_analysis_table = {
    name             = aws_dynamodb_table.resume_analysis.name
    primary_arn      = aws_dynamodb_table.resume_analysis.arn
    primary_region   = local.sites.east.region
    replica_regions  = [local.sites.east.region, local.sites.west.region]
    witness_region   = local.witness_region
    consistency_mode = "STRONG"
  }

  resume_analysis_table_arns = {
    east = aws_dynamodb_table.resume_analysis.arn

    west = replace(
      aws_dynamodb_table.resume_analysis.arn,
      ":${local.sites.east.region}:",
      ":${local.sites.west.region}:",
    )
  }
}
