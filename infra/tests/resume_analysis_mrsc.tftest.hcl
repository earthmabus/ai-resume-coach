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
    condition     = module.shared_foundation.resume_analysis.name == "ai-resume-coach-dev-resume-analysis"
    error_message = "The application table name is incorrect."
  }

  assert {
    condition     = module.shared_foundation.resume_analysis.billing_mode == "PAY_PER_REQUEST"
    error_message = "The MRSC application table must use on-demand billing."
  }

  assert {
    condition = (
      module.shared_foundation.resume_analysis.hash_key == "pk"
      &&
      module.shared_foundation.resume_analysis.range_key == "sk"
    )
    error_message = "The application table must use the pk/sk composite key."
  }

  assert {
    condition = (
      module.shared_foundation.resume_analysis.key_attributes
      == {
        pk     = "S"
        sk     = "S"
        gsi1pk = "S"
        gsi1sk = "S"
        gsi2pk = "S"
        gsi2sk = "S"
      }
    )
    error_message = "The application table must declare string pk/sk plus gsi1 and gsi2 key attributes."
  }

  assert {
    condition = (
      output.resume_analysis_data.global_secondary_indexes.gsi1.name == "gsi1"
      &&
      output.resume_analysis_data.global_secondary_indexes.gsi1.hash_key == "gsi1pk"
      &&
      output.resume_analysis_data.global_secondary_indexes.gsi1.range_key == "gsi1sk"
      &&
      output.resume_analysis_data.global_secondary_indexes.gsi1.projection_type == "ALL"
      &&
      output.resume_analysis_data.global_secondary_indexes.gsi2.name == "gsi2"
      &&
      output.resume_analysis_data.global_secondary_indexes.gsi2.hash_key == "gsi2pk"
      &&
      output.resume_analysis_data.global_secondary_indexes.gsi2.range_key == "gsi2sk"
      &&
      output.resume_analysis_data.global_secondary_indexes.gsi2.projection_type == "ALL"
    )
    error_message = "The exported Resume Analysis data contract must include gsi1 and gsi2."
  }

  assert {
    condition = (
      module.shared_foundation.resume_analysis.replica_regions == ["us-east-1", "us-west-2"]
      &&
      module.shared_foundation.resume_analysis.consistency_mode == "STRONG"
    )
    error_message = "The table must expose us-west-2 as its strong-consistency peer replica."
  }

  assert {
    condition     = module.shared_foundation.resume_analysis.witness_region == "us-east-2"
    error_message = "The MRSC table must expose us-east-2 as its witness."
  }

  assert {
    condition = (
      module.shared_foundation.resume_analysis.pitr_enabled
      &&
      module.shared_foundation.resume_analysis.replica_pitr_enabled
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
