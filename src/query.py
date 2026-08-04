"""
Creates an Athena table over the Firehose-delivered S3 data and runs
example queries to demonstrate the analytics layer of the pipeline.

Usage:
    python src/query.py --setup     # create the table (run once)
    python src/query.py --query     # run example analytics queries
    python src/query.py --setup --query  # do both
"""

import argparse
import json
import os
import time
import boto3
from dotenv import load_dotenv

load_dotenv()

REGION = os.environ.get("AWS_REGION", "us-east-1")
PROFILE = os.environ.get("AWS_PROFILE", "churn-mlops-personal")
DATABASE = os.environ.get("ATHENA_DATABASE", "kinesis_pipeline_dev")
WORKGROUP = os.environ.get("ATHENA_WORKGROUP", "kinesis-pipeline-workgroup")
EVENTS_BUCKET = os.environ.get("EVENTS_BUCKET", "kinesis-pipeline-events-dev")
RESULTS_BUCKET = os.environ.get("RESULTS_BUCKET", "kinesis-pipeline-athena-results-dev")


CREATE_TABLE_SQL = f"""
CREATE EXTERNAL TABLE IF NOT EXISTS customer_events (
    event_id STRING,
    customer_id STRING,
    event_type STRING,
    timestamp STRING,
    contract_type STRING,
    payment_method STRING,
    tenure_months INT,
    monthly_charges DOUBLE,
    session_duration_seconds INT,
    pages_viewed INT
)
PARTITIONED BY (year STRING, month STRING, day STRING)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://{EVENTS_BUCKET}/events/'
TBLPROPERTIES ('has_encrypted_data'='false');
"""

REPAIR_TABLE_SQL = "MSCK REPAIR TABLE customer_events;"

EXAMPLE_QUERIES = [
    (
        "Event count by type",
        "SELECT event_type, COUNT(*) as count FROM customer_events GROUP BY event_type ORDER BY count DESC;"
    ),
    (
        "Event count by contract type",
        "SELECT contract_type, COUNT(*) as count FROM customer_events GROUP BY contract_type ORDER BY count DESC;"
    ),
    (
        "Avg session duration by contract type",
        "SELECT contract_type, ROUND(AVG(session_duration_seconds), 0) as avg_session_secs FROM customer_events GROUP BY contract_type ORDER BY avg_session_secs DESC;"
    ),
    (
        "High-risk customers (month-to-month, short tenure)",
        "SELECT customer_id, tenure_months, monthly_charges FROM customer_events WHERE contract_type = 'Month-to-month' AND tenure_months < 12 GROUP BY customer_id, tenure_months, monthly_charges ORDER BY tenure_months ASC LIMIT 10;"
    ),
]


def get_athena_client():
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    return session.client("athena")


def run_query(athena, sql: str, description: str = "") -> list:
    """Execute a query and wait for results."""
    if description:
        print(f"\n>> {description}")

    response = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": DATABASE},
        WorkGroup=WORKGROUP,
    )
    execution_id = response["QueryExecutionId"]

    # Poll until complete
    while True:
        status = athena.get_query_execution(QueryExecutionId=execution_id)
        state = status["QueryExecution"]["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(1)

    if state != "SUCCEEDED":
        reason = status["QueryExecution"]["Status"].get("StateChangeReason", "Unknown")
        print(f"   Query {state}: {reason}")
        return []

    results = athena.get_query_results(QueryExecutionId=execution_id)
    rows = results["ResultSet"]["Rows"]
    return rows


def print_results(rows: list):
    if not rows:
        print("   (no results)")
        return
    headers = [col["VarCharValue"] for col in rows[0]["Data"]]
    print("   " + " | ".join(f"{h:<25}" for h in headers))
    print("   " + "-" * (28 * len(headers)))
    for row in rows[1:]:
        values = [col.get("VarCharValue", "") for col in row["Data"]]
        print("   " + " | ".join(f"{v:<25}" for v in values))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", action="store_true", help="Create Athena table")
    parser.add_argument("--query", action="store_true", help="Run example queries")
    args = parser.parse_args()

    athena = get_athena_client()

    if args.setup:
        print("Creating Athena table...")
        run_query(athena, CREATE_TABLE_SQL, "CREATE TABLE")
        run_query(athena, REPAIR_TABLE_SQL, "REPAIR TABLE (load partitions)")
        print("Table ready.")

    if args.query:
        print("\nRunning example queries...")
        for description, sql in EXAMPLE_QUERIES:
            rows = run_query(athena, sql, description)
            print_results(rows)

    if not args.setup and not args.query:
        print("Use --setup to create the table, --query to run queries, or both.")


if __name__ == "__main__":
    main()