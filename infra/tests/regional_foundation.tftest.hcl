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

run "regional_storage_and_messaging_are_symmetric" {
  command = plan

  variables {
    # The dev composition intentionally runs the transactional-outbox publisher.
    # Set this explicitly so local auto-loaded tfvars cannot change the contract.
    enable_outbox_publisher_schedule = true
  }

  assert {
    condition = (
      output.regional_foundations.east.document_bucket.name
      == "ai-resume-coach-dev-use1-documents"
    )
    error_message = "The east document-bucket name is incorrect."
  }

  assert {
    condition = (
      output.regional_foundations.west.document_bucket.name
      == "ai-resume-coach-dev-usw2-documents"
    )
    error_message = "The west document-bucket name is incorrect."
  }

  assert {
    condition = (
      output.regional_foundations.east.document_bucket.cors.allowed_origins
      == output.regional_foundations.west.document_bucket.cors.allowed_origins
      && contains(
        output.regional_foundations.east.document_bucket.cors.allowed_origins,
        "https://resume.michaelpopovich.com",
      )
    )
    error_message = "Both regional document buckets must trust the deployed frontend origin."
  }

  assert {
    condition = (
      toset(output.regional_foundations.east.document_bucket.cors.allowed_methods)
      == toset(["GET", "HEAD", "PUT"])
      && toset(output.regional_foundations.west.document_bucket.cors.allowed_methods)
      == toset(["GET", "HEAD", "PUT"])
      && output.regional_foundations.east.document_bucket.cors.allowed_headers == ["*"]
      && output.regional_foundations.west.document_bucket.cors.allowed_headers == ["*"]
      && output.regional_foundations.east.document_bucket.cors.max_age_seconds == 3600
      && output.regional_foundations.west.document_bucket.cors.max_age_seconds == 3600
    )
    error_message = "Regional document-bucket CORS must remain symmetric and support signed browser uploads."
  }

  assert {
    condition = (
      output.regional_foundations.east.processing_queue.name
      == "ai-resume-coach-dev-use1-processing"
    )
    error_message = "The east processing-queue name is incorrect."
  }

  assert {
    condition = (
      output.regional_foundations.west.processing_queue.name
      == "ai-resume-coach-dev-usw2-processing"
    )
    error_message = "The west processing-queue name is incorrect."
  }

  assert {
    condition = (
      output.regional_foundations.east.processing_dlq.name
      == "ai-resume-coach-dev-use1-processing-dlq"
    )
    error_message = "The east processing DLQ name is incorrect."
  }

  assert {
    condition = (
      output.regional_foundations.west.processing_dlq.name
      == "ai-resume-coach-dev-usw2-processing-dlq"
    )
    error_message = "The west processing DLQ name is incorrect."
  }

  assert {
    condition = (
      output.regional_foundations.east.terminal_failure_dlq.name
      == "ai-resume-coach-dev-use1-terminal-failure-dlq"
    )
    error_message = "The east terminal-failure DLQ name is incorrect."
  }

  assert {
    condition = (
      output.regional_foundations.west.terminal_failure_dlq.name
      == "ai-resume-coach-dev-usw2-terminal-failure-dlq"
    )
    error_message = "The west terminal-failure DLQ name is incorrect."
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
    error_message = "Both outbox-publisher schedules must be enabled for the explicit dev composition."
  }

  assert {
    condition = (
      output.regional_sites.east.resourceNamePrefix
      == "ai-resume-coach-dev-use1"
      &&
      output.regional_sites.west.resourceNamePrefix
      == "ai-resume-coach-dev-usw2"
    )
    error_message = "Regional resource prefixes are incorrect."
  }
}
