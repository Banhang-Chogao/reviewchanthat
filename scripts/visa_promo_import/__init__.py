"""
Visa Promo — Import from URL (crawler / parser layer).

Separated from the Visa Promo UI. Reusable for future official sources:
Visa, Mastercard, JCB, Amex, bank promotion pages.

No Cloudflare Worker / R2. Storage remains data/visa-promo.json via the UI.
"""

from .allowlist import is_allowed_url, OFFICIAL_HOST_SUFFIXES
from .crawl_report import CrawlReport, format_report_text
from .normalize import normalize_promotion, dedupe_promotions
from .pipeline import import_from_url

__all__ = [
    "is_allowed_url",
    "OFFICIAL_HOST_SUFFIXES",
    "normalize_promotion",
    "dedupe_promotions",
    "import_from_url",
    "CrawlReport",
    "format_report_text",
]
