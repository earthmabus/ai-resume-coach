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

run "warm_standby_identity_contract_is_explicit" {
  command = plan

  variables {
    enable_frontend_hosting         = false
    enable_cognito_recovery         = true
    registration_notification_email = ""
  }

  assert {
    condition     = output.cognito_recovery.enabled
    error_message = "The Cognito recovery contract must be enabled."
  }

  assert {
    condition     = output.cognito_recovery.mode == "WARM_STANDBY_RESET_REQUIRED"
    error_message = "The recovery mode must disclose password reset requirements."
  }

  assert {
    condition     = !output.cognito_recovery.password_continuity
    error_message = "The contract must not claim password continuity."
  }

  assert {
    condition     = !output.cognito_recovery.automated_failover
    error_message = "The contract must not claim automatic failover."
  }

  assert {
    condition     = output.cognito_recovery.standby.region == "us-west-2"
    error_message = "The standby identity pool must be in us-west-2."
  }
}
