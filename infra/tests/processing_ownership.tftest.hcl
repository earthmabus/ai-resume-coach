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

run "processing_ownership_contract_is_explicit" {
  command = plan

  variables {
    enable_frontend_hosting         = false
    registration_notification_email = ""
  }

  assert {
    condition     = output.processing_ownership.mode == "PERSISTED_OWNER_REGION"
    error_message = "Persisted ownerRegion must remain authoritative."
  }

  assert {
    condition     = output.processing_ownership.worker_enforcement == "FAIL_CLOSED"
    error_message = "Workers must fail closed for non-owner work."
  }

  assert {
    condition     = !output.processing_ownership.automatic_reassignment
    error_message = "The contract must not claim automatic owner reassignment."
  }

  assert {
    condition     = !output.processing_ownership.cross_region_queue_drain
    error_message = "The contract must not claim automatic cross-region queue draining."
  }

  assert {
    condition     = contains(output.processing_ownership.split_brain_protection, "conditional-owner-claim")
    error_message = "Worker claims must guard the persisted owner against transfer races."
  }
}
