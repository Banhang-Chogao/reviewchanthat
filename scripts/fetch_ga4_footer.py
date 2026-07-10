#!/usr/bin/env python3
"""Fetch GA4 summary metrics and write data/ga4_footer.json for static footer display."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "ga4_footer.json"
RANGE = "last_28_days"
RANGE_LABEL = "28 ngày gần nhất"


def now_vn_iso() -> str:
    vn = timezone(timedelta(hours=7))
    return datetime.now(vn).replace(microsecond=0).isoformat()


def load_existing() -> dict | None:
    if not OUTPUT_PATH.exists():
        return None
    try:
        with OUTPUT_PATH.open(encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


def write_payload(payload: dict) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def parse_metric_value(row, index: int) -> int:
    if not row.metric_values or index >= len(row.metric_values):
        return 0
    raw = row.metric_values[index].value or "0"
    try:
        return int(float(raw))
    except ValueError:
        return 0


def fetch_metrics(property_id: str, credentials_info: dict) -> dict:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Filter,
        FilterExpression,
        Metric,
        RunReportRequest,
    )
    from google.oauth2 import service_account

    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    client = BetaAnalyticsDataClient(credentials=credentials)
    property_name = f"properties/{property_id}"
    date_ranges = [DateRange(start_date="28daysAgo", end_date="today")]

    total_request = RunReportRequest(
        property=property_name,
        date_ranges=date_ranges,
        metrics=[
            Metric(name="totalUsers"),
            Metric(name="sessions"),
        ],
    )
    total_response = client.run_report(total_request)
    total_users = 0
    total_sessions = 0
    if total_response.rows:
        row = total_response.rows[0]
        total_users = parse_metric_value(row, 0)
        total_sessions = parse_metric_value(row, 1)

    organic_request = RunReportRequest(
        property=property_name,
        date_ranges=date_ranges,
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[
            Metric(name="totalUsers"),
            Metric(name="sessions"),
        ],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="sessionDefaultChannelGroup",
                string_filter=Filter.StringFilter(value="Organic Search"),
            )
        ),
    )
    organic_response = client.run_report(organic_request)
    organic_users = 0
    organic_sessions = 0
    if organic_response.rows:
        row = organic_response.rows[0]
        organic_users = parse_metric_value(row, 0)
        organic_sessions = parse_metric_value(row, 1)

    return {
        "updated_at": now_vn_iso(),
        "range": RANGE,
        "range_label": RANGE_LABEL,
        "total_users": total_users,
        "total_sessions": total_sessions,
        "organic_search_users": organic_users,
        "organic_search_sessions": organic_sessions,
        "status": "ok",
    }


def error_payload(message: str) -> dict:
    return {
        "updated_at": now_vn_iso(),
        "range": RANGE,
        "range_label": RANGE_LABEL,
        "total_users": 0,
        "total_sessions": 0,
        "organic_search_users": 0,
        "organic_search_sessions": 0,
        "status": "error",
        "error": message,
    }


def main() -> int:
    property_id = os.environ.get("GA4_PROPERTY_ID", "").strip()
    # Accept either bare numeric ID or "properties/123..." form from GA Admin.
    if property_id.startswith("properties/"):
        property_id = property_id.split("/", 1)[1].strip()
    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON", "").strip()
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    existing = load_existing()

    if not property_id:
        print("SKIP: GA4_PROPERTY_ID not set", file=sys.stderr)
        if existing:
            print(f"KEEP: existing {OUTPUT_PATH}", file=sys.stderr)
            return 0
        write_payload(error_payload("GA4_PROPERTY_ID not configured"))
        return 1

    credentials_info = None
    if creds_json:
        try:
            credentials_info = json.loads(creds_json)
        except json.JSONDecodeError as exc:
            print(f"ERROR: invalid GOOGLE_APPLICATION_CREDENTIALS_JSON: {exc}", file=sys.stderr)
            if existing and existing.get("status") == "ok":
                print(f"KEEP: existing {OUTPUT_PATH}", file=sys.stderr)
                return 0
            write_payload(error_payload("invalid credentials JSON"))
            return 1
    elif creds_path and Path(creds_path).exists():
        with Path(creds_path).open(encoding="utf-8") as fh:
            credentials_info = json.load(fh)
    else:
        print("SKIP: GA credentials not set", file=sys.stderr)
        if existing:
            print(f"KEEP: existing {OUTPUT_PATH}", file=sys.stderr)
            return 0
        write_payload(error_payload("GA credentials not configured"))
        return 1

    try:
        payload = fetch_metrics(property_id, credentials_info)
    except Exception as exc:  # noqa: BLE001 - surface API failures safely
        print(f"ERROR: GA4 API failed: {exc}", file=sys.stderr)
        if existing and existing.get("status") == "ok":
            print(f"KEEP: existing {OUTPUT_PATH}", file=sys.stderr)
            return 0
        write_payload(error_payload(str(exc)))
        return 1

    write_payload(payload)
    print(
        "OK: wrote ga4_footer.json "
        f"(users={payload['total_users']}, organic_users={payload['organic_search_users']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())