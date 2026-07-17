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
      length(output.regional_foundations.east.api_gateway.routes.protected) == 7
      &&
      length(output.regional_foundations.west.api_gateway.routes.protected) == 7
    )
    error_message = "Each regional API must expose exactly seven protected routes."
  }

  assert {
    condition = alltrue([
      contains(output.regional_foundations.east.api_gateway.routes.protected, "POST /resume-analysis"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "POST /job-matching"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "POST /resume-tailoring"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "GET /profile"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "PUT /profile"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "DELETE /job-matching/{matchId}"),
      contains(output.regional_foundations.east.api_gateway.routes.protected, "GET /job-matching"),
    ])
    error_message = "The east Region is missing one or more protected application routes."
  }

  assert {
    condition = alltrue([
      contains(output.regional_foundations.west.api_gateway.routes.protected, "POST /resume-analysis"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "POST /job-matching"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "POST /resume-tailoring"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "GET /profile"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "PUT /profile"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "DELETE /job-matching/{matchId}"),
      contains(output.regional_foundations.west.api_gateway.routes.protected, "GET /job-matching"),
    ])
    error_message = "The west Region is missing one or more protected application routes."
  }
}
