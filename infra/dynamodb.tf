resource "aws_dynamodb_table" "resume_analysis" {
  name         = "${local.name_prefix}-resume-analysis"
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "analysisId"

  attribute {
    name = "analysisId"
    type = "S"
  }

  tags = {
    Name = "${local.name_prefix}-resume-analysis"
  }
}
