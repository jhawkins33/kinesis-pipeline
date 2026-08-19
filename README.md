# Kinesis Pipeline

A real-time customer event streaming pipeline built on AWS — simulates
behavioral events from a SaaS customer base, streams them through Kinesis
Firehose into partitioned S3 storage, and makes them queryable via Athena.

Designed as a companion to a churn prediction MLOps project: the same
customer behavioral signals (contract type, tenure, payment method, session
activity) that feed a churn model are streamed here in real time, showing
how fresh data would flow into the ML pipeline.

## Architecture
Producer (Python) ──→ Kinesis Data Firehose ──→ S3 (partitioned by date)
                  │                                       ↓
                  └──→ Kinesis Data Stream ──→ Lambda (real-time churn-risk detection)
                                                          ↓
                                                   CloudWatch Logs
                                              Athena (SQL queries on S3)
## What's here

| Path | Purpose |
|---|---|
| `infrastructure/` | Terraform config — Firehose stream, S3 buckets, IAM role, Athena workgroup + database |
| `src/producer.py` | Simulates customer behavioral events and sends them to Firehose |
| `src/query.py` | Creates the Athena table and runs example analytics queries |
| `src/check_errors.py` | Checks the S3 error prefix for Firehose delivery failures and prints a summary by error type |
| `src/lambda_consumer.py` | Lambda function that processes Kinesis stream events in real time and flags high-churn-risk customers |
| `src/check_errors.py` | Checks the S3 error prefix for Firehose delivery failures and prints a summary by error type |

## Infrastructure

- **Kinesis Data Firehose** — buffers and delivers events to S3, partitioned by `year/month/day`
- **S3 events bucket** — landing zone for Firehose-delivered JSON events
- **S3 Athena results bucket** — stores Athena query results
- **IAM role** — scoped to Firehose with only the S3 permissions it needs
- **Athena workgroup + database** — serverless SQL query layer over the S3 data

All infrastructure is Terraform-managed with remote state in S3.

## Event schema

Each event represents a customer action (login, feature use, support ticket, etc.):

```json
{
  "event_id": "EVT-abc123",
  "customer_id": "CUST-XYZ789",
  "event_type": "login",
  "timestamp": "2026-08-04T22:30:00Z",
  "contract_type": "Month-to-month",
  "payment_method": "Electronic check",
  "tenure_months": 3,
  "monthly_charges": 68.50,
  "session_duration_seconds": 420,
  "pages_viewed": 12
}
```

## Setup

**Prerequisites:** Python 3.12, Terraform >= 1.5, AWS CLI configured with a named profile.

```bash
# 1. Provision infrastructure
cd infrastructure
terraform init
terraform apply

# 2. Set up Python environment
cd ..
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1 on Windows
pip install -r src/requirements.txt

# 3. Configure environment
cp src/.env.example .env
# edit .env with your profile and resource names

# 4. Send events
python src/producer.py --events 100

# 5. Wait ~60 seconds for Firehose to flush to S3, then query
python src/query.py --setup   # run once to create the Athena table
python src/query.py --query   # run analytics queries
```

## Example queries

- Event count by type (login, feature_use, support_ticket, etc.)
- Event distribution by contract type
- Average session duration by contract type
- High-risk customers (month-to-month, short tenure)

## Real-time processing

`src/lambda_consumer.py` is triggered by the Kinesis Data Stream and processes events in real time — no 60-second Firehose buffer. For each event it:

1. Decodes the base64-encoded Kinesis payload
2. Checks for high-churn-risk signals: `contract_type == "Month-to-month"` AND `tenure_months < 12`
3. Logs flagged customers as `HIGH_RISK_EVENT` to CloudWatch with full context (customer ID, event type, tenure, monthly charges)

This mirrors the same feature signals the churn prediction model was trained on — making it possible to flag at-risk customers in real time as they interact with the product, rather than waiting for a nightly batch run.

**Cost note**: Kinesis Data Streams bills per shard-hour (~$0.015/shard/hour). Run `terraform destroy` when not actively using the pipeline, then `terraform apply` to bring it back up.

## Monitoring

- CloudWatch alarm that fires if Firehose DeliveryToS3.Success drops below expected threshold
- CloudWatch alarm on DeliveryToS3.DataFreshness (how far behind delivery is getting)
- **`kinesis-pipeline-firehose-failed-conversion`** — fires immediately if any records fail conversion or processing. Run `python src/check_errors.py` to inspect what landed in the S3 error prefix.

## Cost

All services are pay-per-use with no minimum hourly charge:
- **Firehose**: ~$0.029 per GB ingested
- **S3**: ~$0.023 per GB stored
- **Athena**: ~$5 per TB scanned

For a development/portfolio workload, expect costs in the low cents range.

## Roadmap

- [x] Kinesis Firehose delivery stream with date-partitioned S3 output
- [x] Customer event producer (simulates realistic SaaS behavioral data)
- [x] Athena table with partition discovery and example analytics queries
- [x] Add Lambda consumer for real-time processing alongside the batch layer
- [ ] Connect to churn-mlops: trigger retraining when drift is detected in streaming data
- [x] CloudWatch alarms for Firehose delivery health (delivery success rate + data freshness lag)
- [ ] CloudWatch dashboard for pipeline monitoring (events/sec, delivery latency)