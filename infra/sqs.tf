resource "aws_sqs_queue" "resume_analysis_jobs" {
  name                       = "${local.name_prefix}-resume-analysis-jobs"
  visibility_timeout_seconds = 180
  message_retention_seconds  = 1209600
}
