resource "aws_lambda_layer_version" "pdf_dependencies_east" {
  provider = aws.us_east_1

  layer_name          = "${local.global_name_prefix}-use1-pdf-dependencies"
  description         = "PDF parsing dependencies for regional API Lambdas."
  filename            = data.archive_file.pdf_dependency_layer_zip.output_path
  source_code_hash    = data.archive_file.pdf_dependency_layer_zip.output_base64sha256
  compatible_runtimes = [var.lambda_runtime]

  compatible_architectures = [
    var.lambda_architecture,
  ]
}

resource "aws_lambda_layer_version" "pdf_dependencies_west" {
  provider = aws.us_west_2

  layer_name          = "${local.global_name_prefix}-usw2-pdf-dependencies"
  description         = "PDF parsing dependencies for regional API Lambdas."
  filename            = data.archive_file.pdf_dependency_layer_zip.output_path
  source_code_hash    = data.archive_file.pdf_dependency_layer_zip.output_base64sha256
  compatible_runtimes = [var.lambda_runtime]

  compatible_architectures = [
    var.lambda_architecture,
  ]
}
