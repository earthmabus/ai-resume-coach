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

run "shared_identity_is_created_once" {
  command = plan

  assert {
    condition = (
      module.shared_foundation.identity.name
      == "ai-resume-coach-dev-users"
    )

    error_message = "The shared Cognito pool name is incorrect."
  }

  assert {
    condition = (
      module.shared_foundation.registration_notification.lambda_name
      == "ai-resume-coach-dev-registration-notification"
    )

    error_message = "The registration-notification Lambda name is incorrect."
  }

  assert {
    condition = (
      module.shared_foundation.registration_notification.handler
      == "handler.lambda_handler"
    )

    error_message = "The registration-notification handler is incorrect."
  }

  assert {
    condition = (
      module.shared_foundation.registration_notification.subscription_count
      == 0
    )

    error_message = "An empty email setting must not create a subscription."
  }
}
