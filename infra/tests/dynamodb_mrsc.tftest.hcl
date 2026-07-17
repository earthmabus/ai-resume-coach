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

run "application_table_uses_mrsc_with_witness" {
  command = plan

  assert {
    condition     = aws_dynamodb_table.application.name == "ai-resume-coach-dev-application"
    error_message = "The application table name is incorrect."
  }

  assert {
    condition     = aws_dynamodb_table.application.billing_mode == "PAY_PER_REQUEST"
    error_message = "The MRSC application table must use on-demand billing."
  }

  assert {
    condition = (
      aws_dynamodb_table.application.hash_key == "pk"
      &&
      aws_dynamodb_table.application.range_key == "sk"
    )
    error_message = "The application table must use the pk/sk composite key."
  }

  assert {
    condition = (
      length(aws_dynamodb_table.application.attribute) == 2
      &&
      contains(aws_dynamodb_table.application.attribute[*].name, "pk")
      &&
      contains(aws_dynamodb_table.application.attribute[*].name, "sk")
    )
    error_message = "The application table must declare pk and sk string attributes."
  }

  assert {
    condition = (
      length(aws_dynamodb_table.application.replica) == 1
      &&
      one(aws_dynamodb_table.application.replica).region_name == "us-west-2"
      &&
      one(aws_dynamodb_table.application.replica).consistency_mode == "STRONG"
    )
    error_message = "The table must add us-west-2 as its strong-consistency peer replica."
  }

  assert {
    condition = (
      length(aws_dynamodb_table.application.global_table_witness) == 1
      &&
      one(aws_dynamodb_table.application.global_table_witness).region_name == "us-east-2"
    )
    error_message = "The MRSC table must use us-east-2 as its witness."
  }

  assert {
    condition = (
      one(aws_dynamodb_table.application.point_in_time_recovery).enabled
      &&
      one(aws_dynamodb_table.application.replica).point_in_time_recovery
    )
    error_message = "PITR must be enabled for both active replicas."
  }

  assert {
    condition = (
      output.application_data.consistency_mode == "STRONG"
      &&
      output.application_data.primary_region == "us-east-1"
      &&
      output.application_data.witness_region == "us-east-2"
      &&
      output.application_data.replica_regions == ["us-east-1", "us-west-2"]
    )
    error_message = "The exported application-data topology is incorrect."
  }
}

run "regional_sites_share_the_mrsc_contract" {
  command = plan

  assert {
    condition = (
      output.regional_foundations.east.data_contract.table_name
      ==
      output.regional_foundations.west.data_contract.table_name
    )
    error_message = "Both regional sites must consume the same global table."
  }

  assert {
    condition = (
      output.regional_foundations.east.data_contract.consistency_mode == "STRONG"
      &&
      output.regional_foundations.west.data_contract.consistency_mode == "STRONG"
    )
    error_message = "Both regional sites must be wired for strong consistency."
  }

  assert {
    condition = (
      output.regional_foundations.east.data_contract.witness_region == "us-east-2"
      &&
      output.regional_foundations.west.data_contract.witness_region == "us-east-2"
    )
    error_message = "Both regional sites must identify the same witness Region."
  }
}
