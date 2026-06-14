data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../src/handler.py"
  output_path = "${path.module}/lambda.zip"
}

resource "aws_lambda_function" "api" {
  function_name = "${local.name_prefix}-api"
  role          = aws_iam_role.lambda_execution_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.13"

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  timeout     = 10
  memory_size = 128

  environment {
    variables = {
      PROJECT_NAME          = var.project_name
      ENVIRONMENT           = var.environment
      APP_VERSION           = "0.1.0"
      RESUME_ANALYSIS_TABLE = aws_dynamodb_table.resume_analysis.name
      DOCUMENT_BUCKET       = aws_s3_bucket.documents.bucket
    }
  }
}

layers = [
  aws_lambda_layer_version.pdf_dependencies.arn
]

timeout     = 30
memory_size = 256
