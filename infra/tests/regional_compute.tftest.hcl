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

run "regional_compute_is_symmetric" {
  command = plan

  assert {
    condition = (
      output.regional_foundations.east.compute.api.name
      == "ai-resume-coach-dev-use1-api"
      &&
      output.regional_foundations.west.compute.api.name
      == "ai-resume-coach-dev-usw2-api"
    )
    error_message = "Regional API Lambda names are incorrect."
  }

  assert {
    condition = (
      output.regional_foundations.east.compute.worker.name
      == "ai-resume-coach-dev-use1-worker"
      &&
      output.regional_foundations.west.compute.worker.name
      == "ai-resume-coach-dev-usw2-worker"
    )
    error_message = "Regional worker Lambda names are incorrect."
  }

  assert {
    condition = (
      output.regional_foundations.east.compute.outbox_publisher.name
      == "ai-resume-coach-dev-use1-outbox-publisher"
      &&
      output.regional_foundations.west.compute.outbox_publisher.name
      == "ai-resume-coach-dev-usw2-outbox-publisher"
    )
    error_message = "Regional outbox-publisher Lambda names are incorrect."
  }

  assert {
    condition = (
      output.regional_foundations.east.compute.api.runtime
      == output.regional_foundations.west.compute.api.runtime
      &&
      output.regional_foundations.east.compute.api.architecture
      == output.regional_foundations.west.compute.api.architecture
    )
    error_message = "East and west API Lambdas must use the same runtime and architecture."
  }

  assert {
    condition = (
      output.regional_foundations.east.compute.worker.batch_size
      == 5
      &&
      output.regional_foundations.west.compute.worker.batch_size
      == 5
    )
    error_message = "Both worker event-source mappings must use the configured batch size."
  }

  assert {
    condition = (
      output.regional_foundations.east.compute.worker.enabled
      &&
      output.regional_foundations.west.compute.worker.enabled
    )
    error_message = "Both worker event-source mappings must be enabled."
  }

  assert {
    condition = (
      output.regional_foundations.east.outbox_publisher_schedule.state
      == "DISABLED"
      &&
      output.regional_foundations.west.outbox_publisher_schedule.state
      == "DISABLED"
    )
    error_message = "Outbox publisher schedules must remain disabled until DynamoDB outbox access exists."
  }
}
