moved {
  from = aws_sns_topic.user_registration_notifications
  to   = module.shared_foundation.aws_sns_topic.user_registration_notifications
}

moved {
  from = aws_sns_topic_subscription.user_registration_email
  to   = module.shared_foundation.aws_sns_topic_subscription.user_registration_email
}

moved {
  from = aws_cloudwatch_log_group.registration_notification
  to   = module.shared_foundation.aws_cloudwatch_log_group.registration_notification
}

moved {
  from = aws_iam_role.registration_notification
  to   = module.shared_foundation.aws_iam_role.registration_notification
}

moved {
  from = aws_iam_role_policy_attachment.registration_notification_logging
  to   = module.shared_foundation.aws_iam_role_policy_attachment.registration_notification_logging
}

moved {
  from = aws_iam_role_policy.registration_notification_publish
  to   = module.shared_foundation.aws_iam_role_policy.registration_notification_publish
}

moved {
  from = aws_lambda_function.registration_notification
  to   = module.shared_foundation.aws_lambda_function.registration_notification
}

moved {
  from = aws_cognito_user_pool.users
  to   = module.shared_foundation.aws_cognito_user_pool.users
}

moved {
  from = aws_cognito_user_pool_client.web
  to   = module.shared_foundation.aws_cognito_user_pool_client.web
}

moved {
  from = aws_cognito_user_group.synthetic_runtime_validation
  to   = module.shared_foundation.aws_cognito_user_group.synthetic_runtime_validation
}

moved {
  from = aws_cognito_user_pool_domain.main
  to   = module.shared_foundation.aws_cognito_user_pool_domain.main
}

moved {
  from = aws_lambda_permission.allow_cognito_registration_notification
  to   = module.shared_foundation.aws_lambda_permission.allow_cognito_registration_notification
}

moved {
  from = aws_dynamodb_table.resume_analysis
  to   = module.shared_foundation.aws_dynamodb_table.resume_analysis
}
