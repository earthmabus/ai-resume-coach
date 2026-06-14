resource "null_resource" "pdf_layer_build" {
  triggers = {
    requirements_hash = filesha256("${path.module}/../lambda_layer/requirements.txt")
  }

  provisioner "local-exec" {
    command = <<EOT
      rm -rf ${path.module}/../lambda_layer/build
      mkdir -p ${path.module}/../lambda_layer/build/python
      pip install -r ${path.module}/../lambda_layer/requirements.txt -t ${path.module}/../lambda_layer/build/python
    EOT
  }
}

data "archive_file" "pdf_layer_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda_layer/build"
  output_path = "${path.module}/pdf_layer.zip"

  depends_on = [null_resource.pdf_layer_build]
}

resource "aws_lambda_layer_version" "pdf_dependencies" {
  layer_name          = "${local.name_prefix}-pdf-dependencies"
  filename            = data.archive_file.pdf_layer_zip.output_path
  source_code_hash    = data.archive_file.pdf_layer_zip.output_base64sha256
  compatible_runtimes = ["python3.13"]
}
