locals {
  document_replication_tags = merge(
    local.common_tags,
    {
      Capability = "document-replication"
      Scope      = "multi-region-data"
    },
  )
}

resource "aws_iam_role" "document_replication_east" {
  provider = aws.us_east_1
  count    = var.enable_document_replication ? 1 : 0

  name = "${var.project_name}-${var.environment}-use1-document-replication-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "s3.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = merge(local.document_replication_tags, { Site = "east" })
}

resource "aws_iam_role_policy" "document_replication_east" {
  provider = aws.us_east_1
  count    = var.enable_document_replication ? 1 : 0

  name = "${var.project_name}-${var.environment}-use1-document-replication"
  role = aws_iam_role.document_replication_east[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket",
        ]
        Resource = module.east.document_bucket.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersionTagging",
        ]
        Resource = "${module.east.document_bucket.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags",
        ]
        Resource = "${module.west.document_bucket.arn}/*"
      },
    ]
  })
}

resource "aws_iam_role" "document_replication_west" {
  provider = aws.us_west_2
  count    = var.enable_document_replication ? 1 : 0

  name = "${var.project_name}-${var.environment}-usw2-document-replication-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "s3.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = merge(local.document_replication_tags, { Site = "west" })
}

resource "aws_iam_role_policy" "document_replication_west" {
  provider = aws.us_west_2
  count    = var.enable_document_replication ? 1 : 0

  name = "${var.project_name}-${var.environment}-usw2-document-replication"
  role = aws_iam_role.document_replication_west[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket",
        ]
        Resource = module.west.document_bucket.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersionTagging",
        ]
        Resource = "${module.west.document_bucket.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags",
        ]
        Resource = "${module.east.document_bucket.arn}/*"
      },
    ]
  })
}

resource "aws_s3_bucket_replication_configuration" "documents_east_to_west" {
  provider = aws.us_east_1
  count    = var.enable_document_replication ? 1 : 0

  role   = aws_iam_role.document_replication_east[0].arn
  bucket = module.east.document_bucket.name

  rule {
    id       = "east-to-west-document-replication"
    status   = "Enabled"
    priority = 10

    filter {}

    delete_marker_replication {
      status = "Enabled"
    }

    destination {
      bucket        = module.west.document_bucket.arn
      storage_class = "STANDARD"
    }
  }

  depends_on = [
    aws_iam_role_policy.document_replication_east,
    module.east,
    module.west,
  ]
}

resource "aws_s3_bucket_replication_configuration" "documents_west_to_east" {
  provider = aws.us_west_2
  count    = var.enable_document_replication ? 1 : 0

  role   = aws_iam_role.document_replication_west[0].arn
  bucket = module.west.document_bucket.name

  rule {
    id       = "west-to-east-document-replication"
    status   = "Enabled"
    priority = 10

    filter {}

    delete_marker_replication {
      status = "Enabled"
    }

    destination {
      bucket        = module.east.document_bucket.arn
      storage_class = "STANDARD"
    }
  }

  depends_on = [
    aws_iam_role_policy.document_replication_west,
    module.east,
    module.west,
  ]
}
