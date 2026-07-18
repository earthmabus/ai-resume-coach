data "archive_file" "api_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../build/lambda/api"
  output_path = "${path.module}/api.zip"
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

data "archive_file" "pdf_dependency_layer_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../build/lambda_layer/pdf_dependencies"
  output_path = "${path.module}/pdf_dependency_layer.zip"
}

data "archive_file" "synthetic_health_zip" {
  type        = "zip"
  source_dir  = "${path.module}/synthetics"
  output_path = "${path.root}/.terraform-build/platform-v2-synthetic-health.zip"
}
