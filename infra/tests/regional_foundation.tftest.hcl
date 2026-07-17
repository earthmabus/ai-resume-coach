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
      output.regional_foundations.east.outbox_publisher_schedule.state
      == "DISABLED"
      &&
      output.regional_foundations.west.outbox_publisher_schedule.state
      == "DISABLED"
    )
    error_message = "Both outbox-publisher schedules must remain disabled."
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
