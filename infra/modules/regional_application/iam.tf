locals {
  lambda_assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      },
    ]
  })

  resume_analysis_table_resources = [
    var.resume_analysis.table_arn,
    "${var.resume_analysis.table_arn}/index/*",
  ]
}

resource "aws_iam_role" "api" {
  name               = "${local.name_prefix}-api-role"
  assume_role_policy = local.lambda_assume_role_policy

  tags = merge(
    local.tags,
    {
      Capability = "api-execution"
    },
  )
}

resource "aws_iam_role" "worker" {
  name               = "${local.name_prefix}-worker-role"
  assume_role_policy = local.lambda_assume_role_policy

  tags = merge(
    local.tags,
    {
      Capability = "resume-analysis-worker-execution"
    },
  )
}

resource "aws_iam_role" "outbox_publisher" {
  name               = "${local.name_prefix}-outbox-publisher-role"
  assume_role_policy = local.lambda_assume_role_policy

  tags = merge(
    local.tags,
    {
      Capability = "resume-analysis-outbox-publisher-execution"
    },
  )
}

resource "aws_iam_role_policy_attachment" "api_basic_execution" {
  role       = aws_iam_role.api.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "worker_basic_execution" {
  role       = aws_iam_role.worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "outbox_publisher_basic_execution" {
  role       = aws_iam_role.outbox_publisher.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "api_runtime" {
  name = "${local.name_prefix}-api-runtime"
  role = aws_iam_role.api.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DocumentObjectAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
        ]
        Resource = "${aws_s3_bucket.documents.arn}/*"
      },
      {
        Sid      = "SubmitResumeAnalysisWork"
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = aws_sqs_queue.processing.arn
      },
      {
        Sid    = "ResumeAnalysisDataAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:DeleteItem",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:TransactGetItems",
          "dynamodb:TransactWriteItems",
          "dynamodb:UpdateItem",
        ]
        Resource = local.resume_analysis_table_resources
      },
    ]
  })
}

resource "aws_iam_role_policy" "worker_runtime" {
  name = "${local.name_prefix}-worker-runtime"
  role = aws_iam_role.worker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ConsumeResumeAnalysisWork"
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
        ]
        Resource = aws_sqs_queue.processing.arn
      },
      {
        Sid    = "DocumentObjectAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
        ]
        Resource = "${aws_s3_bucket.documents.arn}/*"
      },
      {
        Sid    = "ResumeAnalysisDataAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:TransactGetItems",
          "dynamodb:TransactWriteItems",
          "dynamodb:UpdateItem",
        ]
        Resource = local.resume_analysis_table_resources
      },
    ]
  })
}

resource "aws_iam_role_policy" "outbox_publisher_runtime" {
  name = "${local.name_prefix}-outbox-publisher-runtime"
  role = aws_iam_role.outbox_publisher.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ResolveRegionalProcessingQueues"
        Effect   = "Allow"
        Action   = ["sqs:GetQueueUrl"]
        Resource = var.regional_transport.processing_queue_arns
      },
      {
        Sid      = "PublishResumeAnalysisWork"
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = var.regional_transport.processing_queue_arns
      },
      {
        Sid    = "ResumeAnalysisOutboxDataAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:TransactWriteItems",
          "dynamodb:UpdateItem",
        ]
        Resource = local.resume_analysis_table_resources
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "api_xray" {
  count = var.observability.active_tracing_enabled ? 1 : 0

  role       = aws_iam_role.api.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

resource "aws_iam_role_policy_attachment" "worker_xray" {
  count = var.observability.active_tracing_enabled ? 1 : 0

  role       = aws_iam_role.worker.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

resource "aws_iam_role_policy_attachment" "outbox_publisher_xray" {
  count = var.observability.active_tracing_enabled ? 1 : 0

  role       = aws_iam_role.outbox_publisher.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}
