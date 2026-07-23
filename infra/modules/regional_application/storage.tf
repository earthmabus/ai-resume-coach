resource "aws_s3_bucket" "documents" {
  bucket        = "${local.name_prefix}-documents"
  force_destroy = var.storage.force_destroy

  tags = merge(
    local.tags,
    {
      Capability = "document-storage"
    },
  )
}

resource "aws_s3_bucket_ownership_controls" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  cors_rule {
    allowed_origins = var.storage.cors_allowed_origins
    allowed_methods = ["GET", "HEAD", "PUT"]
    allowed_headers = ["*"]

    expose_headers = [
      "ETag",
      "x-amz-request-id",
    ]

    max_age_seconds = 3600
  }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }

    bucket_key_enabled = false
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  depends_on = [
    aws_s3_bucket_versioning.documents,
  ]

  rule {
    id     = "regional-document-hygiene"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    noncurrent_version_expiration {
      noncurrent_days = var.storage.noncurrent_version_expiration_days
    }
  }
}
