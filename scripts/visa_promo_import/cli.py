#!/usr/bin/env python3
"""
CLI: crawl an official promotion URL and print/write normalized promotions JSON.

  python3 -m scripts.visa_promo_import.cli \\
    --url 'https://www.visa.com.vn/vi_vn/visa-offers-and-perks/?cardProduct=65&paymentType=9' \\
    --out /tmp/visa-import.json

No Cloudflare Worker. Does not mutate data/visa-promo.json (UI / GitHub save does).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python3 scripts/visa_promo_import/cli.py` from repo root
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.visa_promo_import.pipeline import import_from_url  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Import Visa/issuer promotions from an official URL")
    p.add_argument("--url", required=True, help="Official promotion listing URL")
    p.add_argument("--out", help="Write JSON result to this path")
    p.add_argument("--skip-expired", action="store_true", help="Drop expired offers")
    p.add_argument("--browser", action="store_true", help="Prefer Playwright/Selenium rendering")
    p.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = p.parse_args(argv)

    report = import_from_url(
        args.url,
        skip_expired=args.skip_expired,
        prefer_browser=args.browser,
    )
    payload = {
        "report": report.as_dict(),
        "promotions": report.promotions,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(
            f"Wrote {len(report.promotions)} promotions → {args.out} "
            f"(imported={report.imported} skipped={report.skipped} failures={len(report.failures)})",
            file=sys.stderr,
        )
    else:
        print(text)

    if report.failures and not report.promotions:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
