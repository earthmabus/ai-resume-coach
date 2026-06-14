output "api_endpoint" {
  description = "Base URL for the HTTP API."
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}

output "health_check_url" {
  description = "Health check endpoint."
  value       = "${aws_apigatewayv2_api.http_api.api_endpoint}/health"
}

output "lambda_function_name" {
  description = "Lambda function name."
  value       = aws_lambda_function.api.function_name
}
