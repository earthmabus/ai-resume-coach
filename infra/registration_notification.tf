resource "aws_sns_topic" "user_registration_notifications" {
  name = "${local.name_prefix}-user-registration-notifications"
}

resource "aws_sns_topic_subscription" "user_registration_email" {
  topic_arn = aws_sns_topic.user_registration_notifications.arn
  protocol  = "email"
  endpoint  = var.registration_notification_email
}
