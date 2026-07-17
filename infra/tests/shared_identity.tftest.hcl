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
      aws_cognito_user_pool.users.name
      == "ai-resume-coach-dev-users"
    )

    error_message = "The shared Cognito pool name is incorrect."
  }

  assert {
    condition = (
      aws_lambda_function.registration_notification.function_name
      == "ai-resume-coach-dev-registration-notification"
    )

    error_message = "The registration-notification Lambda name is incorrect."
  }

  assert {
    condition = (
      aws_lambda_function.registration_notification.handler
      == "handler.lambda_handler"
    )

    error_message = "The registration-notification handler is incorrect."
  }

  assert {
    condition = (
      length(aws_sns_topic_subscription.user_registration_email)
      == 0
    )

    error_message = "An empty email setting must not create a subscription."
  }
}
