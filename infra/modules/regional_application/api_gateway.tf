locals {
  public_api_routes = toset([
    "GET /health",
    "GET /health/live",
    "GET /health/ready",
  ])

  protected_api_routes = toset([
    "DELETE /job-matching/{matchId}",
    "GET /job-matching",
    "GET /profile",
    "POST /job-matching",
    "POST /resume-analysis",
    "POST /resume-tailoring",
    "PUT /profile",
  ])

  api_access_log_format = jsonencode({
    timestamp           = "$context.requestTime"
    level               = "INFO"
    service             = "regional-http-api"
    component           = "api-gateway"
    operation           = "$context.routeKey"
    requestId           = "$context.requestId"
    correlationId       = "$context.requestId"
    deploymentId        = var.runtime.deployment_id
    architectureVersion = var.architecture_version
    region              = var.region
    site                = var.site_name
    httpMethod          = "$context.httpMethod"
    routeKey            = "$context.routeKey"
    status              = "$context.status"
    protocol            = "$context.protocol"
    responseLength      = "$context.responseLength"
    integrationError    = "$context.integrationErrorMessage"
    sourceIp            = "$context.identity.sourceIp"
    userAgent           = "$context.identity.userAgent"
  })
}

resource "aws_cloudwatch_log_group" "api_access" {
  name              = "/aws/apigateway/${local.name_prefix}-http-api"
  retention_in_days = var.api.access_log_retention_days

  tags = merge(local.tags, { Capability = "api-access-logs" })
}

resource "aws_apigatewayv2_api" "regional" {
  name          = "${local.name_prefix}-http-api"
  description   = "Regional HTTP API for the AI Resume Coach."
  protocol_type = "HTTP"

  cors_configuration {
    allow_credentials = false
    allow_headers = [
      "Authorization",
      "Content-Type",
      "X-Request-Id",
    ]
    allow_methods = [
      "DELETE",
      "GET",
      "OPTIONS",
      "POST",
      "PUT",
    ]
    allow_origins = var.api.cors_allowed_origins
    expose_headers = [
      "X-Request-Id",
    ]
    max_age = 300
  }

  tags = merge(local.tags, { Capability = "regional-http-api" })
}

resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.regional.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "${local.name_prefix}-cognito-jwt"

  jwt_configuration {
    audience = [var.identity.client_id]
    issuer   = var.identity.issuer
  }
}

resource "aws_apigatewayv2_integration" "api_lambda" {
  api_id = aws_apigatewayv2_api.regional.id

  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 29000
}

resource "aws_apigatewayv2_route" "public" {
  for_each = local.public_api_routes

  api_id    = aws_apigatewayv2_api.regional.id
  route_key = each.value
  target    = "integrations/${aws_apigatewayv2_integration.api_lambda.id}"

  authorization_type = "NONE"
}

resource "aws_apigatewayv2_route" "protected" {
  for_each = local.protected_api_routes

  api_id    = aws_apigatewayv2_api.regional.id
  route_key = each.value
  target    = "integrations/${aws_apigatewayv2_integration.api_lambda.id}"

  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_stage" "default" {
  api_id = aws_apigatewayv2_api.regional.id

  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_access.arn
    format          = local.api_access_log_format
  }

  default_route_settings {
    detailed_metrics_enabled = false
    throttling_burst_limit   = var.api.throttling_burst_limit
    throttling_rate_limit    = var.api.throttling_rate_limit
  }

  tags = merge(local.tags, { Capability = "regional-http-api-stage" })
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowRegionalHttpApiInvocation"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.regional.execution_arn}/*/*"
}
