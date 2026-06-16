data "archive_file" "worker_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/worker.zip"
}

resource "aws_lambda_function" "resume_analysis_worker" {
  function_name = "${local.name_prefix}-resume-analysis-worker"
  role          = aws_iam_role.lambda_execution_role.arn
  handler       = "worker.lambda_handler"
  runtime       = "python3.13"

  filename         = data.archive_file.worker_zip.output_path
  source_code_hash = data.archive_file.worker_zip.output_base64sha256

  layers = [
    aws_lambda_layer_version.pdf_dependencies.arn
  ]

  timeout     = 180
  memory_size = 512

  environment {
    variables = {
      PROJECT_NAME          = var.project_name
      ENVIRONMENT           = var.environment
      APP_VERSION           = "0.1.0"
      RESUME_ANALYSIS_TABLE = aws_dynamodb_table.resume_analysis.name
      DOCUMENT_BUCKET       = aws_s3_bucket.documents.bucket
      ANALYSIS_PROVIDER     = var.analysis_provider
      OPENAI_MODEL          = var.openai_model
      OPENAI_API_KEY        = var.openai_api_key
      RESUME_ANALYSIS_QUEUE_URL = aws_sqs_queue.resume_analysis_jobs.url
    }
  }
}

resource "aws_lambda_event_source_mapping" "resume_analysis_worker_sqs" {
  event_source_arn = aws_sqs_queue.resume_analysis_jobs.arn
  function_name    = aws_lambda_function.resume_analysis_worker.arn
  batch_size       = 1
}
