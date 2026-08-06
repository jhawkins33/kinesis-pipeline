import os
import boto3
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

PROFILE = os.environ.get("AWS_PROFILE", "churn-mlops-personal")
REGION = os.environ.get("AWS_REGION", "us-east-1")
EVENTS_BUCKET = os.environ.get("EVENTS_BUCKET", "kinesis-pipeline-events-dev")
ERRORS_PREFIX = "errors/"


def main():
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    s3 = session.client("s3")

    # Note: list_objects_v2 returns max 1000 objects. If error volume
    # exceeds this, add pagination via NextContinuationToken.
    response = s3.list_objects_v2(
        Bucket=EVENTS_BUCKET,
        Prefix=ERRORS_PREFIX,
    )
    objects = response.get("Contents", [])

    total_files = 0
    total_size = 0
    errors_by_type = defaultdict(lambda: {"count": 0, "size": 0})

    for obj in objects:
        key = obj["Key"]
        size = obj["Size"]
        path_parts = key.split("/")
        if len(path_parts) < 3 or not path_parts[1]:
            continue
        error_type = path_parts[1]
        total_files += 1
        total_size += size
        errors_by_type[error_type]["count"] += 1
        errors_by_type[error_type]["size"] += size

    print("Bucket:", EVENTS_BUCKET)
    print("Prefix:", ERRORS_PREFIX)
    print("Total error files:", total_files)
    print("Total size:", total_size, "bytes")
    print()
    print("Breakdown by error type:")
    if not errors_by_type:
        print("  No error files found.")
        return
    for error_type, details in sorted(errors_by_type.items()):
        print(" ", error_type + ":",
              details["count"], "file(s),",
              details["size"], "bytes")


if __name__ == "__main__":
    main()