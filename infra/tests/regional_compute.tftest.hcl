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

  # Pin the normal dev operating profile explicitly so local auto-loaded
  # terraform.tfvars files cannot change this contract test's behavior.
  variables {
    enable_outbox_publisher_schedule = true
  }

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
      output.regional_foundations.east.compute.api.handler
      == "handler.lambda_handler"
      &&
      output.regional_foundations.west.compute.api.handler
      == "handler.lambda_handler"
      &&
      output.regional_foundations.east.compute.worker.handler
      == "handler.lambda_handler"
      &&
      output.regional_foundations.west.compute.worker.handler
      == "handler.lambda_handler"
      &&
      output.regional_foundations.east.compute.outbox_publisher.handler
      == "handler.handler"
      &&
      output.regional_foundations.west.compute.outbox_publisher.handler
      == "handler.handler"
    )
    error_message = "Regional Lambda handlers must match their packaged module entrypoints."
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
      output.regional_foundations.east.compute.worker.dependency_layer_count == 1
      &&
      output.regional_foundations.west.compute.worker.dependency_layer_count == 1
    )
    error_message = "Each regional worker Lambda must receive the shared dependency layer used by its providers."
  }

  assert {
    condition = (
      module.shared_foundation.registration_notification.dependency_layers == 0
      &&
      output.regional_foundations.east.compute.outbox_publisher.dependency_layer_count == 0
      &&
      output.regional_foundations.west.compute.outbox_publisher.dependency_layer_count == 0
    )
    error_message = "The shared dependency layer must be attached to API and worker Lambdas only."
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
      contains(
        output.regional_foundations.east.compute.api.runtime_policy_actions,
        "dynamodb:DescribeTable",
      )
      &&
      contains(
        output.regional_foundations.west.compute.api.runtime_policy_actions,
        "dynamodb:DescribeTable",
      )
      &&
      contains(
        output.regional_foundations.east.compute.api.runtime_policy_actions,
        "sqs:GetQueueAttributes",
      )
      &&
      contains(
        output.regional_foundations.west.compute.api.runtime_policy_actions,
        "sqs:GetQueueAttributes",
      )
    )
    error_message = "API runtime roles must include only the read-only dependency checks required by /health/ready."
  }

  assert {
    condition = (
      contains(
        output.regional_foundations.east.compute.outbox_publisher.runtime_policy_actions,
        "dynamodb:Query",
      )
      &&
      contains(
        output.regional_foundations.west.compute.outbox_publisher.runtime_policy_actions,
        "dynamodb:Query",
      )
      &&
      !contains(
        output.regional_foundations.east.compute.outbox_publisher.runtime_policy_actions,
        "dynamodb:Scan",
      )
      &&
      !contains(
        output.regional_foundations.west.compute.outbox_publisher.runtime_policy_actions,
        "dynamodb:Scan",
      )
      &&
      contains(
        output.regional_foundations.east.compute.outbox_publisher.runtime_policy_resources,
        "table/index/*",
      )
      &&
      contains(
        output.regional_foundations.west.compute.outbox_publisher.runtime_policy_resources,
        "table/index/*",
      )
    )
    error_message = "Publisher IAM must cover table indexes for Query without granting Scan."
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
      == "ENABLED"
      &&
      output.regional_foundations.west.outbox_publisher_schedule.state
      == "ENABLED"
      &&
      output.regional_foundations.east.outbox_publisher_schedule.enabled
      &&
      output.regional_foundations.west.outbox_publisher_schedule.enabled
    )
    error_message = "The normal dev operating profile must enable both outbox publisher schedules so queued work is dispatched."
  }
}

run "regional_outbox_publisher_schedules_can_be_disabled_for_dev" {
  command = plan

  # Exercise the explicit disabled mode independently from repository-local
  # terraform.tfvars values.
  variables {
    enable_outbox_publisher_schedule = false
  }

  assert {
    condition = (
      output.regional_foundations.east.outbox_publisher_schedule.state
      == "DISABLED"
      &&
      output.regional_foundations.west.outbox_publisher_schedule.state
      == "DISABLED"
      &&
      !output.regional_foundations.east.outbox_publisher_schedule.enabled
      &&
      !output.regional_foundations.west.outbox_publisher_schedule.enabled
    )
    error_message = "Outbox publisher schedules must support an explicitly disabled dev mode."
  }

  assert {
    condition = (
      output.regional_foundations.east.outbox_publisher_schedule.schedule_expression
      == output.regional_foundations.west.outbox_publisher_schedule.schedule_expression
      &&
      output.regional_foundations.east.outbox_publisher_schedule.schedule_expression
      == "rate(1 minute)"
    )
    error_message = "Regional outbox publisher schedules must keep the same configured expression."
  }

  assert {
    condition = (
      output.regional_foundations.east.outbox_publisher_schedule.target_id
      == "regional-outbox-publisher"
      &&
      output.regional_foundations.west.outbox_publisher_schedule.target_id
      == "regional-outbox-publisher"
    )
    error_message = "Each regional outbox schedule must expose the expected target id."
  }

  assert {
    condition = (
      output.regional_foundations.east.outbox_publisher_schedule.target_function
      == output.regional_foundations.east.compute.outbox_publisher.name
      &&
      output.regional_foundations.west.outbox_publisher_schedule.target_function
      == output.regional_foundations.west.compute.outbox_publisher.name
    )
    error_message = "Each regional outbox schedule must target the local publisher Lambda."
  }

  assert {
    condition = (
      output.regional_foundations.east.outbox_publisher_schedule.permission_statement_id
      == "AllowEventBridgeOutboxPublisher"
      &&
      output.regional_foundations.west.outbox_publisher_schedule.permission_statement_id
      == "AllowEventBridgeOutboxPublisher"
      &&
      output.regional_foundations.east.outbox_publisher_schedule.permission_principal
      == "events.amazonaws.com"
      &&
      output.regional_foundations.west.outbox_publisher_schedule.permission_principal
      == "events.amazonaws.com"
    )
    error_message = "Publisher invoke permissions must allow EventBridge invocation with the expected statement."
  }
}

run "regional_outbox_publisher_schedule_enablement_is_dev_only" {
  command = plan

  variables {
    environment                         = "prod"
    enable_outbox_publisher_schedule    = true
    enable_observability_dashboard      = false
    enable_synthetic_placement_override = false
    production_readiness_enforced       = false
  }

  expect_failures = [var.enable_outbox_publisher_schedule]
}
