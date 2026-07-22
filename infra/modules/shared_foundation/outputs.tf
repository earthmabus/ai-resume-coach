output "identity" {
  description = "Shared identity capability contract consumed by regional sites and validation."

  value = {
    name          = aws_cognito_user_pool.users.name
    user_pool_id  = aws_cognito_user_pool.users.id
    user_pool_arn = aws_cognito_user_pool.users.arn
    client_id     = aws_cognito_user_pool_client.web.id
    domain        = aws_cognito_user_pool_domain.main.domain
    issuer        = "https://cognito-idp.${var.east_region}.amazonaws.com/${aws_cognito_user_pool.users.id}"
  }
}

output "registration_notification" {
  description = "Shared registration-notification capability contract."

  value = {
    lambda_name        = aws_lambda_function.registration_notification.function_name
    handler            = aws_lambda_function.registration_notification.handler
    dependency_layers  = length(coalesce(aws_lambda_function.registration_notification.layers, []))
    topic_arn          = aws_sns_topic.user_registration_notifications.arn
    subscription_count = length(aws_sns_topic_subscription.user_registration_email)
  }
}

output "resume_analysis" {
  description = "DynamoDB MRSC Resume Analysis system-of-record capability contract."

  value = {
    name             = aws_dynamodb_table.resume_analysis.name
    primary_arn      = aws_dynamodb_table.resume_analysis.arn
    billing_mode     = aws_dynamodb_table.resume_analysis.billing_mode
    hash_key         = aws_dynamodb_table.resume_analysis.hash_key
    range_key        = aws_dynamodb_table.resume_analysis.range_key
    key_attributes   = { for attribute in aws_dynamodb_table.resume_analysis.attribute : attribute.name => attribute.type }
    primary_region   = var.east_region
    replica_regions  = [var.east_region, var.west_region]
    witness_region   = var.witness_region
    consistency_mode = "STRONG"
    pitr_enabled     = one(aws_dynamodb_table.resume_analysis.point_in_time_recovery).enabled
    replica_pitr_enabled = one(
      aws_dynamodb_table.resume_analysis.replica
    ).point_in_time_recovery
  }
}

output "resume_analysis_table_arns" {
  description = "Regional ARNs for the shared DynamoDB MRSC table."

  value = {
    east = aws_dynamodb_table.resume_analysis.arn

    west = replace(
      aws_dynamodb_table.resume_analysis.arn,
      ":${var.east_region}:",
      ":${var.west_region}:",
    )
  }
}
