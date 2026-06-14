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

output "frontend_bucket_name" {
  description = "S3 bucket hosting the frontend website."
  value       = aws_s3_bucket.frontend.bucket
}

output "frontend_website_endpoint" {
  description = "S3 static website endpoint."
  value       = aws_s3_bucket_website_configuration.frontend.website_endpoint
}

output "resume_analysis_table_name" {
  description = "DynamoDB table storing resume analyses."
  value       = aws_dynamodb_table.resume_analysis.name
}

output "document_bucket_name" {
  description = "S3 bucket storing uploaded resume documents."
  value       = aws_s3_bucket.documents.bucket
}
