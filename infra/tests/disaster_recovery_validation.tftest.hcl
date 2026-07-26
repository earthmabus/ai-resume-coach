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

run "disaster_recovery_validation_contract_is_explicit" {
  command = plan

  variables {
    enable_frontend_hosting         = false
    registration_notification_email = ""
  }

  assert {
    condition     = output.disaster_recovery_validation.mode == "CONTROL_PLANE_AND_BOUNDED_DATA_PATH"
    error_message = "The DR-validation mode must remain explicit."
  }

  assert {
    condition     = !output.disaster_recovery_validation.actual_outage_injection
    error_message = "MS-022 must not claim that it injects a real regional outage."
  }

  assert {
    condition     = output.disaster_recovery_validation.document_sentinel_bidirectional
    error_message = "The exercise must validate both document-replication directions."
  }

  assert {
    condition     = !output.disaster_recovery_validation.identity_failover_exercised
    error_message = "The contract must not claim seamless Cognito failover testing."
  }

  assert {
    condition     = !output.disaster_recovery_validation.processing_owner_transfer_exercised
    error_message = "The contract must not claim automatic owner transfer testing."
  }
}
