#!/usr/bin/env python3
"""
Send a binary CloudEvent carrying a Firestore DocumentEventData protobuf to the
local check-push-data function endpoint. This constructs the protobuf using
google.events types, serializes to bytes, and POSTs with the CloudEvents
binary-mode headers so the function receives raw bytes (not JSON/dict).

Usage: python3 scripts/send_firestore_cloudevent.py [--host HOST] [--project PROJECT]

Requires: pip install google-events protobuf requests
"""
import argparse
import uuid
from datetime import datetime, timezone
import requests
import sys

try:
    from google.events.cloud.firestore import DocumentEventData, Document
    from google.protobuf import json_format
except Exception as e:
    print("Missing Python dependencies. Install: pip install google-events protobuf requests")
    raise


def build_event_bytes(project: str, collection: str = "orders") -> bytes:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    uid = uuid.uuid4().hex[:8]
    resource_name = f"projects/{project}/databases/(default)/documents/{collection}/TEST-{uid}"

    value = {
        "name": resource_name,
        "fields": {
            "orderId": {"stringValue": f"TEST-{uid}"},
            "dateOrder": {"stringValue": now},
            "totalOrder": {"doubleValue": 125.75},
        },
        "createTime": now,
        "updateTime": now,
    }

    doc = Document()
    json_format.ParseDict(value, doc)

    ev = DocumentEventData()
    ev.value.CopyFrom(doc)

    return ev.SerializeToString()


def send(host: str, project: str):
    payload = build_event_bytes(project)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    headers = {
        "Content-Type": "application/protobuf",
        "ce-id": uuid.uuid4().hex,
        "ce-specversion": "1.0",
        "ce-time": now,
        "ce-type": "google.cloud.firestore.document.v1.created",
        "ce-source": f"//firestore.googleapis.com/projects/{project}/databases/(default)",
    }

    url = f"{host.rstrip('/')}/"
    resp = requests.post(url, data=payload, headers=headers)
    print("POST", url)
    print("Status:", resp.status_code)
    print(resp.text)


def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="http://localhost:8083", help="Function host URL (default http://localhost:8083)")
    p.add_argument("--project", default=None, help="GOOGLE_CLOUD_PROJECT to use for resource names")
    p.add_argument("--collection", default="orders", help="Collection name to use")
    args = p.parse_args(argv)

    project = args.project or ("local-project")
    try:
        send(args.host, project)
    except Exception as e:
        print("Error sending event:", e)
        raise


if __name__ == "__main__":
    main(sys.argv[1:])
