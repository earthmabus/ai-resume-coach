data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../build/lambda/api"
  output_path = "${path.module}/lambda.zip"
}

data "archive_file" "worker_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../build/lambda/worker"
  output_path = "${path.module}/worker.zip"
}

data "archive_file" "outbox_publisher_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../build/lambda/outbox_publisher"
  output_path = "${path.module}/outbox_publisher.zip"
}

data "archive_file" "registration_notification_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../build/lambda/registration_notification"
  output_path = "${path.module}/registration_notification.zip"
}
