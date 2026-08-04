"""
Simulates customer behavioral events and sends them to Kinesis Firehose.

Events represent actions a SaaS customer might take — logins, feature
usage, support tickets — the kind of data that feeds churn prediction
models with fresh signal.

Usage:
    python src/producer.py --events 100
    python src/producer.py --events 1000 --delay 0.01
"""

import argparse
import json
import os
import random
import time
from datetime import datetime, timezone
import boto3
from dotenv import load_dotenv

load_dotenv()

REGION = os.environ.get("AWS_REGION", "us-east-1")
PROFILE = os.environ.get("AWS_PROFILE", "churn-mlops-personal")
STREAM_NAME = os.environ.get("FIREHOSE_STREAM_NAME", "kinesis-pipeline-events")

# Customer segments — mirrors the churn dataset's contract types
CONTRACT_TYPES = ["Month-to-month", "One year", "Two year"]
PAYMENT_METHODS = ["Electronic check", "Mailed check", "Bank transfer", "Credit card"]
EVENT_TYPES = ["login", "feature_use", "support_ticket", "plan_view", "logout"]

# High-churn-risk customers tend to have month-to-month contracts and
# electronic check payments — same patterns the churn model learned
CHURN_RISK_WEIGHTS = {
    "Month-to-month": 0.6,
    "One year": 0.3,
    "Two year": 0.1,
}


def generate_customer_id():
    return "CUST-" + "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=8))


def generate_event(customer_pool: list) -> dict:
    customer = random.choice(customer_pool)
    return {
        "event_id": "EVT-" + "".join(random.choices("0123456789abcdef", k=12)),
        "customer_id": customer["customer_id"],
        "event_type": random.choice(EVENT_TYPES),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "contract_type": customer["contract_type"],
        "payment_method": customer["payment_method"],
        "tenure_months": customer["tenure_months"],
        "monthly_charges": customer["monthly_charges"],
        "session_duration_seconds": random.randint(30, 3600),
        "pages_viewed": random.randint(1, 50),
    }


def build_customer_pool(size: int = 100) -> list:
    """Generate a stable pool of simulated customers to draw events from."""
    customers = []
    contract_types = random.choices(
        CONTRACT_TYPES,
        weights=[60, 25, 15],  # skewed toward month-to-month (higher churn risk)
        k=size,
    )
    for i in range(size):
        contract = contract_types[i]
        customers.append({
            "customer_id": generate_customer_id(),
            "contract_type": contract,
            "payment_method": random.choice(PAYMENT_METHODS),
            "tenure_months": random.randint(1, 72),
            "monthly_charges": round(random.uniform(20, 120), 2),
        })
    return customers


def send_events(n_events: int, delay: float = 0.05):
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    firehose = session.client("firehose")

    customer_pool = build_customer_pool(size=200)
    print(f"Sending {n_events} events to '{STREAM_NAME}'...")

    sent = 0
    errors = 0

    for i in range(n_events):
        event = generate_event(customer_pool)
        record = json.dumps(event) + "\n"  # newline delimiter for Athena

        try:
            firehose.put_record(
                DeliveryStreamName=STREAM_NAME,
                Record={"Data": record.encode("utf-8")},
            )
            sent += 1
        except Exception as e:
            errors += 1
            print(f"  Error on event {i+1}: {e}")

        if (i + 1) % 25 == 0 or (i + 1) == n_events:
            print(f"  {i + 1}/{n_events} sent")

        if delay > 0:
            time.sleep(delay)

    print(f"\nDone. {sent} sent, {errors} errors.")
    print("Note: Firehose buffers for ~60 seconds before delivering to S3.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=100, help="Number of events to send")
    parser.add_argument("--delay", type=float, default=0.05, help="Delay between events in seconds")
    args = parser.parse_args()

    send_events(args.events, args.delay)


if __name__ == "__main__":
    main()