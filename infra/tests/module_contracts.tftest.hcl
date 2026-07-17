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

run "sites_are_symmetric_peers" {
  command = plan

  assert {
    condition = (
      output.regional_sites.east.role
      == output.regional_sites.west.role
    )

    error_message = "East and west must have the same Region role."
  }

  assert {
    condition = (
      output.regional_sites.east.architectureVersion
      == output.regional_sites.west.architectureVersion
    )

    error_message = "East and west must use the same architecture version."
  }

  assert {
    condition = (
      output.regional_sites.east.deploymentId
      == output.regional_sites.west.deploymentId
    )

    error_message = "East and west must receive the same deployment ID."
  }
}
