resource "aws_apigatewayv2_api" "http_api" {
  name          = "${local.name_prefix}-http-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["content-type"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_origins = ["*"]
  }
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "health_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "version_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /version"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "analyze_resume_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /analyze-resume"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "list_analyses_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /analyses"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "get_analysis_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /analysis/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "resume_upload_url_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /resume-upload-url"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "analyze_uploaded_resume_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /analyze-uploaded-resume"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "allow_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

resource "aws_apigatewayv2_route" "match_job_description_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /match-job-description"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "list_job_matches_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /job-matches"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "get_job_match_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /job-match/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}
