data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/lambda.zip"
}

resource "aws_lambda_function" "api" {
  function_name = "${local.name_prefix}-api"
  role          = aws_iam_role.lambda_execution_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.13"

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  layers = [
    aws_lambda_layer_version.pdf_dependencies.arn
  ]

  timeout     = 600
  memory_size = 1024

  environment {
    variables = {
      PROJECT_NAME              = var.project_name
      ENVIRONMENT               = var.environment
      APP_VERSION               = var.app_version
      DEPLOYMENT_ID             = var.deployment_id
      LOG_LEVEL                 = var.log_level

      RESUME_ANALYSIS_TABLE     = aws_dynamodb_table.resume_analysis.name
      DOCUMENT_BUCKET           = aws_s3_bucket.documents.bucket
      ANALYSIS_PROVIDER         = var.analysis_provider

      OPENAI_MODEL              = var.openai_model
      OPENAI_API_KEY            = var.openai_api_key
      RESUME_ANALYSIS_QUEUE_URL = aws_sqs_queue.resume_analysis_jobs.url
    }
  }
}
