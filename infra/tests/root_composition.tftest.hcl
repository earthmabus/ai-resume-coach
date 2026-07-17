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

run "platform_v2_composes_two_active_sites" {
  command = plan

  assert {
    condition     = output.architecture_version == "platform-v2"
    error_message = "The root architecture version must be platform-v2."
  }

  assert {
    condition     = output.east_region == "us-east-1"
    error_message = "The east site must use us-east-1."
  }

  assert {
    condition     = output.west_region == "us-west-2"
    error_message = "The west site must use us-west-2."
  }

  assert {
    condition     = output.witness_region == "us-east-2"
    error_message = "The reserved witness Region must be us-east-2."
  }

  assert {
    condition = (
      output.regional_sites.east.resourceNamePrefix
      == "ai-resume-coach-dev-use1"
    )

    error_message = "The east resource prefix is incorrect."
  }

  assert {
    condition = (
      output.regional_sites.west.resourceNamePrefix
      == "ai-resume-coach-dev-usw2"
    )

    error_message = "The west resource prefix is incorrect."
  }
}
