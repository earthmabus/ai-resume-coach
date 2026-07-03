resource "aws_s3_bucket" "frontend" {
  bucket = "${local.name_prefix}-frontend-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

#resource "aws_s3_bucket_public_access_block" "frontend" {
#  bucket = aws_s3_bucket.frontend.id
#
#  block_public_acls       = true
#  block_public_policy     = true
#  ignore_public_acls      = true
#  restrict_public_buckets = true
#}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }
}

resource "aws_s3_bucket_policy" "frontend_public_read" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.frontend.arn}/*"
      }
    ]
  })
}

#resource "aws_s3_bucket_policy" "frontend_cloudfront_read" {
#  bucket = aws_s3_bucket.frontend.id
#
#  policy = jsonencode({
#    Version = "2012-10-17"
#    Statement = [
#      {
#       Sid    = "AllowCloudFrontRead"
#       Effect = "Allow"
#       Principal = {
#         Service = "cloudfront.amazonaws.com"
#       }
#       Action   = "s3:GetObject"
#       Resource = "${aws_s3_bucket.frontend.arn}/*"
#       Condition = {
#          StringEquals = {
#            "AWS:SourceArn" = aws_cloudfront_distribution.frontend.arn
#          }
#        }
#      }
#    ]
#  })
#}

resource "aws_s3_object" "frontend_files" {
  for_each = fileset("${path.module}/../frontend", "**/*")

  bucket = aws_s3_bucket.frontend.id
  key    = each.value
  source = "${path.module}/../frontend/${each.value}"
  etag   = filemd5("${path.module}/../frontend/${each.value}")

  content_type = lookup(
    {
      html = "text/html"
      css  = "text/css"
      js   = "application/javascript"
    },
    split(".", each.value)[length(split(".", each.value)) - 1],
    "application/octet-stream"
  )
}

resource "aws_s3_object" "frontend_config" {
  bucket = aws_s3_bucket.frontend.id
  key    = "config.js"

  content = <<EOT
window.APP_CONFIG = {
  apiEndpoint: "${aws_apigatewayv2_api.http_api.api_endpoint}",
  cognitoRegion: "${var.aws_region}",
  cognitoUserPoolId: "${aws_cognito_user_pool.users.id}",
  cognitoUserPoolClientId: "${aws_cognito_user_pool_client.web.id}"
};
EOT

  content_type = "application/javascript"
}

data "aws_caller_identity" "current" {}
