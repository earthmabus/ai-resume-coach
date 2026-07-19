resource "aws_sqs_queue" "terminal_failure" {
  name = "${local.name_prefix}-terminal-failure-dlq"

  message_retention_seconds = var.messaging.dlq_retention_seconds
  sqs_managed_sse_enabled   = true

  tags = merge(
    local.tags,
    {
      Capability = "workflow-terminal-failure-dlq"
    },
  )
}

resource "aws_sqs_queue" "processing_dlq" {
  name = "${local.name_prefix}-processing-dlq"

  message_retention_seconds  = var.messaging.dlq_retention_seconds
  sqs_managed_sse_enabled    = true
  visibility_timeout_seconds = var.messaging.visibility_timeout_seconds

  tags = merge(
    local.tags,
    {
      Capability = "processing-dead-letter-queue"
    },
  )
}

resource "aws_sqs_queue" "processing" {
  name = "${local.name_prefix}-processing"

  message_retention_seconds  = var.messaging.queue_retention_seconds
  receive_wait_time_seconds  = 20
  sqs_managed_sse_enabled    = true
  visibility_timeout_seconds = var.messaging.visibility_timeout_seconds

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.processing_dlq.arn
    maxReceiveCount     = var.messaging.max_receive_count
  })

  tags = merge(
    local.tags,
    {
      Capability = "processing-queue"
    },
  )
}

resource "aws_cloudwatch_event_rule" "outbox_publisher_schedule" {
  name                = "${local.name_prefix}-outbox-publisher-schedule"
  description         = "Regional trigger for the transactional outbox publisher."
  schedule_expression = var.messaging.publisher_schedule
  state               = var.messaging.publisher_schedule_enabled ? "ENABLED" : "DISABLED"

  tags = merge(
    local.tags,
    {
      Capability = "outbox-publisher-schedule"
    },
  )
}
