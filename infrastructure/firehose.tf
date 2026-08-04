resource "aws_kinesis_firehose_delivery_stream" "events" {
  name        = "${var.project}-events"
  destination = "extended_s3"

  extended_s3_configuration {
    role_arn           = aws_iam_role.firehose.arn
    bucket_arn         = aws_s3_bucket.events.arn
    buffering_size     = 64
    buffering_interval = 60
    prefix             = "events/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/"
    error_output_prefix = "errors/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/"

    compression_format = "UNCOMPRESSED"
  }
}