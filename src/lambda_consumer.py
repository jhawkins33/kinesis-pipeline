"""
Real-time churn risk detector and metrics publisher — Lambda consumer for Kinesis Data Stream.

Triggered by the kinesis-pipeline-stream, processes events in batches,
flags high-risk customers, logs them to CloudWatch, and publishes
aggregate batch metrics (event volume, risk counts, per-type breakdown)
as custom CloudWatch metrics.

High-risk criteria (mirrors the churn model's learned patterns):
  - contract_type == "Month-to-month"  AND
  - tenure_months < 12
"""

import base64
import json
import os
from collections import Counter

import boto3

PROJECT = os.environ.get("PROJECT", "kinesis-pipeline")
METRIC_NAMESPACE = os.environ.get("METRIC_NAMESPACE", PROJECT)

cloudwatch = boto3.client("cloudwatch")


def is_high_risk(event: dict) -> bool:
    """Return True if the customer event matches high-churn-risk criteria."""
    return (
        event.get("contract_type") == "Month-to-month"
        and event.get("tenure_months", 99) < 12
    )


def publish_metrics(total: int, flagged: int, type_counts: Counter):
    """Publish aggregate batch metrics as custom CloudWatch metrics."""
    metric_data = [
        {"MetricName": "EventsProcessed", "Value": total, "Unit": "Count"},
        {"MetricName": "HighRiskEvents", "Value": flagged, "Unit": "Count"},
    ]
    for event_type, count in type_counts.items():
        metric_data.append({
            "MetricName": "EventsByType",
            "Value": count,
            "Unit": "Count",
            "Dimensions": [{"Name": "EventType", "Value": event_type}],
        })

    try:
        cloudwatch.put_metric_data(Namespace=METRIC_NAMESPACE, MetricData=metric_data)
    except Exception as e:
        # A metrics-publishing failure shouldn't fail the whole batch
        print(f"[{PROJECT}] WARNING: failed to publish CloudWatch metrics: {e}")


def handler(event, context):
    """
    Lambda entry point. Kinesis delivers records in batches — process
    each one, decode the base64 payload, flag high-risk customers, and
    publish aggregate metrics for the batch.
    """
    total = len(event["Records"])
    flagged = 0
    type_counts = Counter()

    for record in event["Records"]:
        # Kinesis data is base64-encoded
        raw = base64.b64decode(record["kinesis"]["data"]).decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            print(f"[{PROJECT}] WARNING: could not parse record: {raw[:100]}")
            continue

        event_id = payload.get("event_id", "unknown")
        customer_id = payload.get("customer_id", "unknown")
        event_type = payload.get("event_type", "unknown")
        type_counts[event_type] += 1

        if is_high_risk(payload):
            flagged += 1
            print(
                f"[{PROJECT}] HIGH_RISK_EVENT "
                f"customer={customer_id} "
                f"event={event_type} "
                f"contract={payload.get('contract_type')} "
                f"tenure={payload.get('tenure_months')}mo "
                f"monthly_charges=${payload.get('monthly_charges')} "
                f"event_id={event_id}"
            )
        else:
            print(
                f"[{PROJECT}] OK "
                f"customer={customer_id} "
                f"event={event_type} "
                f"event_id={event_id}"
            )

    publish_metrics(total, flagged, type_counts)

    print(f"[{PROJECT}] Batch complete: {total} records, {flagged} high-risk flagged.")
    return {"statusCode": 200, "processed": total, "flagged": flagged}