#!/usr/bin/env python3
"""Submit the public sitemap to Google Search Console.

This is the supported automation path for a normal blog. Google's Indexing API is
limited to job posting and livestreaming video pages, while Search Console's
public API supports sitemap submission for ordinary sites.
"""

from __future__ import annotations

import json
import os
import sys
from urllib.parse import quote

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account


SCOPES = ["https://www.googleapis.com/auth/webmasters"]
DEFAULT_SITE_URL = "https://banhang-chogao.github.io/reviewchanthat/"
DEFAULT_SITEMAP_URL = "https://banhang-chogao.github.io/reviewchanthat/sitemap.xml"


def load_credentials_info() -> dict | None:
    raw_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON", "").strip()
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

    if raw_json:
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError as exc:
            print(f"ERROR: invalid GOOGLE_APPLICATION_CREDENTIALS_JSON: {exc}", file=sys.stderr)
            return None

    if path:
        try:
            with open(path, encoding="utf-8") as handle:
                return json.load(handle)
        except OSError as exc:
            print(f"ERROR: cannot read GOOGLE_APPLICATION_CREDENTIALS: {exc}", file=sys.stderr)
            return None
        except json.JSONDecodeError as exc:
            print(f"ERROR: invalid credentials file JSON: {exc}", file=sys.stderr)
            return None

    print("SKIP: Google credentials are not configured.", file=sys.stderr)
    return None


def submit_sitemap(site_url: str, sitemap_url: str, credentials_info: dict) -> None:
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=SCOPES,
    )
    session = AuthorizedSession(credentials)
    endpoint = (
        "https://www.googleapis.com/webmasters/v3/sites/"
        f"{quote(site_url, safe='')}/sitemaps/{quote(sitemap_url, safe='')}"
    )
    response = session.put(endpoint, timeout=30)
    if response.status_code == 403:
        print(f"WARN: Search Console API not enabled (403) — sitemap submission skipped.", file=sys.stderr)
        return
    if response.status_code not in (200, 204):
        print(f"ERROR: Search Console sitemap submit failed ({response.status_code})", file=sys.stderr)
        print(response.text[:1000], file=sys.stderr)
        response.raise_for_status()
    print(f"Submitted sitemap to Google Search Console: {sitemap_url}")


def main() -> int:
    credentials_info = load_credentials_info()
    if not credentials_info:
        return 0

    site_url = os.environ.get("GSC_SITE_URL", DEFAULT_SITE_URL).strip() or DEFAULT_SITE_URL
    sitemap_url = os.environ.get("GSC_SITEMAP_URL", DEFAULT_SITEMAP_URL).strip() or DEFAULT_SITEMAP_URL

    try:
        submit_sitemap(site_url, sitemap_url, credentials_info)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
