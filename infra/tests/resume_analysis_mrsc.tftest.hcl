mock_provider "aws" {
  alias = "us_east_1"
}

mock_provider "aws" {
  alias = "us_west_2"
}

mock_provider "aws" {
  alias = "us_east_2"
}

mock_provider "archive" {}

run "resume_analysis_system_of_record_uses_mrsc_with_witness" {
  command = plan

  assert {
    condition     = aws_dynamodb_table.resume_analysis.name == "ai-resume-coach-dev-resume-analysis"
    error_message = "The application table name is incorrect."
  }

  assert {
    condition     = aws_dynamodb_table.resume_analysis.billing_mode == "PAY_PER_REQUEST"
    error_message = "The MRSC application table must use on-demand billing."
  }

  assert {
    condition = (
      aws_dynamodb_table.resume_analysis.hash_key == "pk"
      &&
      aws_dynamodb_table.resume_analysis.range_key == "sk"
    )
    error_message = "The application table must use the pk/sk composite key."
  }

  assert {
    condition = (
      length(aws_dynamodb_table.resume_analysis.attribute) == 2
      &&
      contains(aws_dynamodb_table.resume_analysis.attribute[*].name, "pk")
      &&
      contains(aws_dynamodb_table.resume_analysis.attribute[*].name, "sk")
    )
    error_message = "The application table must declare pk and sk string attributes."
  }

  assert {
    condition = (
      length(aws_dynamodb_table.resume_analysis.replica) == 1
      &&
      one(aws_dynamodb_table.resume_analysis.replica).region_name == "us-west-2"
      &&
      one(aws_dynamodb_table.resume_analysis.replica).consistency_mode == "STRONG"
    )
    error_message = "The table must add us-west-2 as its strong-consistency peer replica."
  }

  assert {
    condition = (
      length(aws_dynamodb_table.resume_analysis.global_table_witness) == 1
      &&
      one(aws_dynamodb_table.resume_analysis.global_table_witness).region_name == "us-east-2"
    )
    error_message = "The MRSC table must use us-east-2 as its witness."
  }

  assert {
    condition = (
      one(aws_dynamodb_table.resume_analysis.point_in_time_recovery).enabled
      &&
      one(aws_dynamodb_table.resume_analysis.replica).point_in_time_recovery
    )
    error_message = "PITR must be enabled for both active replicas."
  }

  assert {
    condition = (
      output.resume_analysis_data.consistency_mode == "STRONG"
      &&
      output.resume_analysis_data.primary_region == "us-east-1"
      &&
      output.resume_analysis_data.witness_region == "us-east-2"
      &&
      output.resume_analysis_data.replica_regions == ["us-east-1", "us-west-2"]
    )
    error_message = "The exported application-data topology is incorrect."
  }
}

run "regional_sites_share_the_resume_analysis_mrsc_contract" {
  command = plan

  assert {
    condition = (
      output.regional_foundations.east.resume_analysis.table_name
      ==
      output.regional_foundations.west.resume_analysis.table_name
    )
    error_message = "Both regional sites must consume the same global table."
  }

  assert {
    condition = (
      output.regional_foundations.east.resume_analysis.consistency_mode == "STRONG"
      &&
      output.regional_foundations.west.resume_analysis.consistency_mode == "STRONG"
    )
    error_message = "Both regional sites must be wired for strong consistency."
  }

  assert {
    condition = (
      output.regional_foundations.east.resume_analysis.witness_region == "us-east-2"
      &&
      output.regional_foundations.west.resume_analysis.witness_region == "us-east-2"
    )
    error_message = "Both regional sites must identify the same witness Region."
  }
}
