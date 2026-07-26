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

run "bidirectional_document_replication_contract_is_explicit" {
  command = plan

  variables {
    enable_frontend_hosting         = false
    enable_document_replication     = true
    registration_notification_email = ""
  }

  assert {
    condition     = output.document_replication.enabled
    error_message = "Document replication must be enabled."
  }

  assert {
    condition     = output.document_replication.mode == "BIDIRECTIONAL_CRR"
    error_message = "Both active sites must replicate newly written document versions."
  }

  assert {
    condition     = output.document_replication.east.destination_region == "us-west-2"
    error_message = "East documents must replicate to us-west-2."
  }

  assert {
    condition     = output.document_replication.west.destination_region == "us-east-1"
    error_message = "West documents must replicate to us-east-1."
  }

  assert {
    condition     = !output.document_replication.existing_objects
    error_message = "The contract must disclose that ordinary CRR does not backfill existing objects."
  }

  assert {
    condition     = !output.document_replication.rtc_enabled
    error_message = "Replication Time Control must remain disabled unless explicitly approved."
  }
}
