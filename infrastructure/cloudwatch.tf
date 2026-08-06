resource "aws_cloudwatch_metric_alarm" "firehose_delivery_success" {
  alarm_name          = "${var.project}-firehose-delivery-success"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DeliveryToS3.Success"
  namespace           = "AWS/Firehose"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Firehose has not successfully delivered to S3 in two consecutive 5-minute periods. Check the Firehose console for delivery errors and verify IAM permissions on the S3 bucket."

  dimensions = {
    DeliveryStreamName = aws_kinesis_firehose_delivery_stream.events.name
  }
}

resource "aws_cloudwatch_metric_alarm" "firehose_data_freshness" {
  alarm_name          = "${var.project}-firehose-data-freshness"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DeliveryToS3.DataFreshness"
  namespace           = "AWS/Firehose"
  period              = 300
  statistic           = "Maximum"
  threshold           = 300
  alarm_description   = "Firehose delivery lag exceeds 5 minutes — oldest undelivered record is more than 300 seconds old. Check for S3 throttling, IAM issues, or unusually high ingest volume."

  dimensions = {
    DeliveryStreamName = aws_kinesis_firehose_delivery_stream.events.name
  }
}

resource "aws_cloudwatch_metric_alarm" "firehose_failed_conversion" {
  alarm_name          = "${var.project}-firehose-failed-conversion"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FailedConversion.Records"
  namespace           = "AWS/Firehose"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "One or more records failed conversion/processing in Firehose. Check the S3 error prefix (errors/) for dropped records and investigate the error type."

  dimensions = {
    DeliveryStreamName = aws_kinesis_firehose_delivery_stream.events.name
  }
}