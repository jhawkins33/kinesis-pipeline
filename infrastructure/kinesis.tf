resource "aws_kinesis_stream" "events" {
  name        = "${var.project}-stream"
  shard_count = 1

  retention_period = 24

  tags = {
    Environment = var.environment
    Project     = var.project
  }
}