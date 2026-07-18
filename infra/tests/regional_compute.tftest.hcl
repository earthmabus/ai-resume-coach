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
      output.regional_foundations.east.compute.api.dependency_layer_count == 1
      &&
      output.regional_foundations.west.compute.api.dependency_layer_count == 1
    )
    error_message = "Each regional API Lambda must receive one PDF dependency layer."
  }

  assert {
    condition = (
      aws_lambda_layer_version.pdf_dependencies_east.layer_name
      == "ai-resume-coach-dev-use1-pdf-dependencies"
      &&
      aws_lambda_layer_version.pdf_dependencies_west.layer_name
      == "ai-resume-coach-dev-usw2-pdf-dependencies"
    )
    error_message = "Regional PDF dependency layers must be named for their local active region."
  }

  assert {
    condition = (
      length(coalesce(aws_lambda_function.registration_notification.layers, [])) == 0
      &&
      output.regional_foundations.east.compute.worker.dependency_layer_count == 0
      &&
      output.regional_foundations.west.compute.worker.dependency_layer_count == 0
      &&
      output.regional_foundations.east.compute.outbox_publisher.dependency_layer_count == 0
      &&
      output.regional_foundations.west.compute.outbox_publisher.dependency_layer_count == 0
    )
    error_message = "The PDF dependency layer must be attached only to API Lambdas."
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
      output.regional_foundations.east.routing.current_region == "us-east-1"
      &&
      output.regional_foundations.east.routing.primary_region == "us-east-1"
      &&
      length(output.regional_foundations.east.routing.secondary_regions) == 1
      &&
      contains(output.regional_foundations.east.routing.secondary_regions, "us-west-2")
      &&
      output.regional_foundations.west.routing.current_region == "us-west-2"
      &&
      output.regional_foundations.west.routing.primary_region == "us-east-1"
      &&
      length(output.regional_foundations.west.routing.secondary_regions) == 1
      &&
      contains(output.regional_foundations.west.routing.secondary_regions, "us-west-2")
    )
    error_message = "Regional routing configuration must identify current, primary, and secondary regions."
  }

  assert {
    condition = (
      output.regional_foundations.east.regional_transport.processing_queue_names_by_region["us-east-1"]
      == "ai-resume-coach-dev-use1-processing"
      &&
      output.regional_foundations.east.regional_transport.processing_queue_names_by_region["us-west-2"]
      == "ai-resume-coach-dev-usw2-processing"
      &&
      output.regional_foundations.west.regional_transport.processing_queue_names_by_region["us-east-1"]
      == "ai-resume-coach-dev-use1-processing"
      &&
      output.regional_foundations.west.regional_transport.processing_queue_names_by_region["us-west-2"]
      == "ai-resume-coach-dev-usw2-processing"
    )
    error_message = "Regional transport must expose active processing queue names to both outbox publishers."
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
