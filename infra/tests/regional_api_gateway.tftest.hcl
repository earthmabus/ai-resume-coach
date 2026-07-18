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

run "regional_http_apis_are_symmetric" {
  command = plan

  assert {
    condition = (
      output.regional_foundations.east.api_gateway.name
      == "ai-resume-coach-dev-use1-http-api"
      &&
      output.regional_foundations.west.api_gateway.name
      == "ai-resume-coach-dev-usw2-http-api"
    )
    error_message = "Regional HTTP API names are incorrect."
  }

  assert {
    condition = (
      output.regional_foundations.east.api_gateway.protocol_type == "HTTP"
      &&
      output.regional_foundations.west.api_gateway.protocol_type == "HTTP"
    )
    error_message = "Both regional APIs must use the low-cost HTTP API protocol."
  }

  assert {
    condition = (
      output.regional_foundations.east.api_gateway.stage.name == "$default"
      &&
      output.regional_foundations.west.api_gateway.stage.name == "$default"
      &&
      output.regional_foundations.east.api_gateway.stage.auto_deploy
      &&
      output.regional_foundations.west.api_gateway.stage.auto_deploy
    )
    error_message = "Both regional APIs must use auto-deployed default stages."
  }

  assert {
    condition = (
      output.regional_foundations.east.api_gateway.stage.log_group
      == "/aws/apigateway/ai-resume-coach-dev-use1-http-api"
      &&
      output.regional_foundations.west.api_gateway.stage.log_group
      == "/aws/apigateway/ai-resume-coach-dev-usw2-http-api"
    )
    error_message = "Regional API access log groups are incorrect."
  }

  assert {
    condition = (
      output.regional_foundations.east.api_gateway.authorizer.name
      == "ai-resume-coach-dev-use1-cognito-jwt"
      &&
      output.regional_foundations.west.api_gateway.authorizer.name
      == "ai-resume-coach-dev-usw2-cognito-jwt"
    )
    error_message = "Regional Cognito JWT authorizer names are incorrect."
  }
}

run "health_is_public_and_application_routes_are_protected" {
  command = plan

  assert {
    condition = (
      output.regional_foundations.east.api_gateway.authorizer.type == "JWT"
      &&
      output.regional_foundations.west.api_gateway.authorizer.type == "JWT"
    )
    error_message = "Both regional APIs must use JWT authorizers."
  }

  assert {
    condition = (
      length(output.regional_foundations.east.api_gateway.authorizer.identity_sources) == 1
      &&
      contains(
        output.regional_foundations.east.api_gateway.authorizer.identity_sources,
        "$request.header.Authorization",
      )
      &&
      length(output.regional_foundations.west.api_gateway.authorizer.identity_sources) == 1
      &&
      contains(
        output.regional_foundations.west.api_gateway.authorizer.identity_sources,
        "$request.header.Authorization",
      )
    )
    error_message = "Both JWT authorizers must read bearer tokens only from the Authorization header."
  }

  assert {
    condition = (
      length(output.regional_foundations.east.api_gateway.routes.public) == 3
      &&
      length(output.regional_foundations.west.api_gateway.routes.public) == 3
    )
    error_message = "Each regional API must expose exactly three public routes."
  }

  assert {
    condition = (
      contains(output.regional_foundations.east.api_gateway.routes.public, "GET /health")
      &&
      contains(output.regional_foundations.east.api_gateway.routes.public, "GET /health/live")
      &&
      contains(output.regional_foundations.east.api_gateway.routes.public, "GET /health/ready")
      &&
      contains(output.regional_foundations.west.api_gateway.routes.public, "GET /health")
      &&
      contains(output.regional_foundations.west.api_gateway.routes.public, "GET /health/live")
      &&
      contains(output.regional_foundations.west.api_gateway.routes.public, "GET /health/ready")
    )
    error_message = "The three health endpoints must be publicly accessible in both Regions."
  }

  assert {
    condition = (
      length(output.regional_foundations.east.api_gateway.routes.protected) == 21
      &&
      length(output.regional_foundations.west.api_gateway.routes.protected) == 21
    )
    error_message = "Each regional API must expose the authoritative protected route inventory."
  }

  assert {
    condition = alltrue([
      contains(output.regional_foundations.east.api_gateway.routes.protected, "DELETE /analysis/{id}"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "DELETE /analyses"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "DELETE /job-match/{id}"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "DELETE /job-matches"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "GET /analyses"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "GET /analysis/{id}"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "GET /analysis/{id}/download-url"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "GET /job-match/{id}"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "GET /job-match/{matchId}/interview-prep"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "GET /job-match/{matchId}/tailoring"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "GET /job-matches"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "GET /profile"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "GET /resume-tailoring/{id}"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "GET /target-career"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "POST /analyze-resume"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "POST /analyze-uploaded-resume"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "POST /match-job-description"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "POST /resume-upload-url"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "POST /tailor-resume"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "PUT /profile"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "PUT /target-career"),
    ])
    error_message = "The east Region protected routes must match the application route contract."
  }

  assert {
    condition = alltrue([
      contains(output.regional_foundations.west.api_gateway.routes.protected, "DELETE /analysis/{id}"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "DELETE /analyses"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "DELETE /job-match/{id}"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "DELETE /job-matches"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "GET /analyses"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "GET /analysis/{id}"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "GET /analysis/{id}/download-url"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "GET /job-match/{id}"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "GET /job-match/{matchId}/interview-prep"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "GET /job-match/{matchId}/tailoring"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "GET /job-matches"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "GET /profile"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "GET /resume-tailoring/{id}"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "GET /target-career"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "POST /analyze-resume"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "POST /analyze-uploaded-resume"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "POST /match-job-description"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "POST /resume-upload-url"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "POST /tailor-resume"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "PUT /profile"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "PUT /target-career"),
    ])
    error_message = "The west Region protected routes must match the application route contract."
  }

  assert {
    condition = alltrue([
      !contains(output.regional_foundations.east.api_gateway.routes.protected, "DELETE /job-matching/{matchId}"),
      !contains(output.regional_foundations.east.api_gateway.routes.protected, "GET /job-matching"),
      !contains(output.regional_foundations.east.api_gateway.routes.protected, "POST /job-matching"),
      !contains(output.regional_foundations.east.api_gateway.routes.protected, "POST /resume-analysis"),
      !contains(output.regional_foundations.east.api_gateway.routes.protected, "POST /resume-tailoring"),
    ])
    error_message = "The east Region must not expose obsolete legacy route keys."
  }

  assert {
    condition = alltrue([
      !contains(output.regional_foundations.west.api_gateway.routes.protected, "DELETE /job-matching/{matchId}"),
      !contains(output.regional_foundations.west.api_gateway.routes.protected, "GET /job-matching"),
      !contains(output.regional_foundations.west.api_gateway.routes.protected, "POST /job-matching"),
      !contains(output.regional_foundations.west.api_gateway.routes.protected, "POST /resume-analysis"),
      !contains(output.regional_foundations.west.api_gateway.routes.protected, "POST /resume-tailoring"),
    ])
    error_message = "The west Region must not expose obsolete legacy route keys."
  }

  assert {
    condition = (
      output.regional_foundations.east.api_gateway.routes.protected
      ==
      output.regional_foundations.west.api_gateway.routes.protected
    )
    error_message = "East and west protected route sets must be identical."
  }
}

run "synthetic_placement_override_is_disabled_by_default" {
  command = plan

  assert {
    condition = (
      !output.regional_foundations.east.validation.synthetic_placement_override.enabled
      &&
      !output.regional_foundations.west.validation.synthetic_placement_override.enabled
    )
    error_message = "Synthetic placement override must be disabled by default."
  }

  assert {
    condition = (
      !contains(
        output.regional_foundations.east.validation.synthetic_placement_override.active_regions,
        output.witness_region,
      )
      &&
      !contains(
        output.regional_foundations.west.validation.synthetic_placement_override.active_regions,
        output.witness_region,
      )
    )
    error_message = "The witness Region must not be selectable as an active owner region."
  }
}

run "synthetic_placement_override_can_be_enabled_for_dev" {
  command = plan

  variables {
    enable_synthetic_placement_override = true
  }

  assert {
    condition = (
      output.regional_foundations.east.validation.synthetic_placement_override.enabled
      &&
      output.regional_foundations.west.validation.synthetic_placement_override.enabled
    )
    error_message = "Synthetic placement override should be explicitly enableable for dev validation."
  }

  assert {
    condition = (
      output.regional_foundations.east.validation.synthetic_placement_override.group_name
      == "synthetic-runtime-validation"
      &&
      output.regional_foundations.west.validation.synthetic_placement_override.group_name
      == "synthetic-runtime-validation"
    )
    error_message = "Synthetic placement override must use the dedicated validation Cognito group."
  }

  assert {
    condition = (
      !contains(
        output.regional_foundations.east.validation.synthetic_placement_override.active_regions,
        output.witness_region,
      )
      &&
      !contains(
        output.regional_foundations.west.validation.synthetic_placement_override.active_regions,
        output.witness_region,
      )
    )
    error_message = "The witness Region must remain excluded when synthetic placement override is enabled."
  }
}
