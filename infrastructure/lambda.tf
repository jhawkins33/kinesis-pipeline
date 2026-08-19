# Package the Lambda function code
data "archive_file" "lambda_consumer" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda_consumer.py"
  output_path = "${path.module}/../src/lambda_consumer.zip"
}

resource "aws_lambda_function" "consumer" {
  filename         = data.archive_file.lambda_consumer.output_path
  function_name    = "${var.project}-consumer"
  role             = aws_iam_role.lambda.arn
  handler          = "lambda_consumer.handler"
  runtime          = "python3.12"
  source_code_hash = data.archive_file.lambda_consumer.output_base64sha256

  environment {
    variables = {
      PROJECT = var.project
    }
  }
}

# Trigger: Lambda reads from the Kinesis stream
resource "aws_lambda_event_source_mapping" "kinesis" {
  event_source_arn  = aws_kinesis_stream.events.arn
  function_name     = aws_lambda_function.consumer.arn
  starting_position = "LATEST"
  batch_size        = 10
}