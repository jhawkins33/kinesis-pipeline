"""
Real-time churn risk detector — Lambda consumer for Kinesis Data Stream.

Triggered by the kinesis-pipeline-stream, processes events in batches,
flags high-risk customers, and logs them to CloudWatch.

High-risk criteria (mirrors the churn model's learned patterns):
  - contract_type == "Month-to-month"  AND
  - tenure_months < 12
"""

import base64
import json
import os

PROJECT = os.environ.get("PROJECT", "kinesis-pipeline")


def is_high_risk(event: dict) -> bool:
    """Return True if the customer event matches high-churn-risk criteria."""
    return (
        event.get("contract_type") == "Month-to-month"
        and event.get("tenure_months", 99) < 12
    )


def handler(event, context):
    """
    Lambda entry point. Kinesis delivers records in batches — process
    each one, decode the base64 payload, and flag high-risk customers.
    """
    total = len(event["Records"])
    flagged = 0

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

    print(f"[{PROJECT}] Batch complete: {total} records, {flagged} high-risk flagged.")
    return {"statusCode": 200, "processed": total, "flagged": flagged}