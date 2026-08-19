resource "aws_athena_workgroup" "main" {
  name = "${var.project}-workgroup"
  force_destroy = true
  configuration {
    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/results/"
    }
  }
}

resource "aws_athena_database" "events" {
  name   = replace("${var.project}_${var.environment}", "-", "_")
  bucket = aws_s3_bucket.athena_results.bucket
}