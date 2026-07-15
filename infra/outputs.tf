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

output "frontend_cloudfront_domain" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "frontend_https_url" {
  description = "HTTPS URL for the frontend"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "frontend_custom_domain_url" {
  description = "Custom HTTPS URL for the frontend"
  value       = "https://resume.michaelpopovich.com"
}

output "resume_analysis_table_name" {
  description = "DynamoDB table storing resume analyses."
  value       = aws_dynamodb_table.resume_analysis.name
}

output "document_bucket_name" {
  description = "S3 bucket storing uploaded resume documents."
  value       = aws_s3_bucket.documents.bucket
}

output "resume_analysis_queue_url" {
  description = "SQS queue URL for asynchronous resume analysis jobs."
  value       = aws_sqs_queue.resume_analysis_jobs.url
}

output "resume_analysis_worker_function_name" {
  description = "Lambda worker function that processes asynchronous resume analysis jobs."
  value       = aws_lambda_function.resume_analysis_worker.function_name
}

output "outbox_publisher_function_name" {
  description = "Lambda function that publishes transactional outbox events to SQS."
  value       = aws_lambda_function.outbox_publisher.function_name
}

output "outbox_publisher_schedule_name" {
  description = "EventBridge schedule rule that invokes the outbox publisher."
  value       = aws_cloudwatch_event_rule.outbox_publisher_schedule.name
}

output "cognito_user_pool_id" {
  value       = aws_cognito_user_pool.users.id
  description = "Cognito User Pool ID"
}

output "cognito_user_pool_client_id" {
  value       = aws_cognito_user_pool_client.web.id
  description = "Cognito User Pool Web Client ID"
}

output "cloudfront_domain_name" {
  value = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.frontend.id
}
