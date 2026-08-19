output "firehose_stream_name" {
  value = aws_kinesis_firehose_delivery_stream.events.name
}

output "events_bucket" {
  value = aws_s3_bucket.events.bucket
}

output "athena_results_bucket" {
  value = aws_s3_bucket.athena_results.bucket
}

output "athena_database" {
  value = aws_athena_database.events.name
}

output "athena_workgroup" {
  value = aws_athena_workgroup.main.name
}

output "kinesis_stream_name" {
  value = aws_kinesis_stream.events.name
}

output "lambda_function_name" {
  value = aws_lambda_function.consumer.function_name
}