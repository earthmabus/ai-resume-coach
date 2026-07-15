resource "aws_sqs_queue" "resume_analysis_dlq" {
  name                      = "${local.name_prefix}-resume-analysis-dlq"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "resume_analysis_jobs" {
  name                       = "${local.name_prefix}-resume-analysis-jobs"
  visibility_timeout_seconds = 420
  message_retention_seconds  = 1209600

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.resume_analysis_dlq.arn
    maxReceiveCount     = 5
  })
}

resource "aws_sqs_queue_redrive_allow_policy" "resume_analysis_dlq" {
  queue_url = aws_sqs_queue.resume_analysis_dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns = [
      aws_sqs_queue.resume_analysis_jobs.arn
    ]
  })
}
