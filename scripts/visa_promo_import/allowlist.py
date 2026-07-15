"""Official domain allowlist — never scrape unrelated hosts."""

from __future__ import annotations

from urllib.parse import urlparse

OFFICIAL_HOST_SUFFIXES = (
    "visa.com",
    "visa.com.vn",
    "mastercard.com",
    "mastercard.com.vn",
    "jcb.co.jp",
    "americanexpress.com",
    "hsbc.com.vn",
    "hsbc.com",
    "vietcombank.com.vn",
    "techcombank.com.vn",
    "vpbank.com.vn",
    "tpb.vn",
    "mbbank.com.vn",
    "sacombank.com.vn",
    "bidv.com.vn",
    "acb.com.vn",
    "homeandaway.hsbc.com",
)


def _host_allowed(host: str) -> bool:
    host = (host or "").lower().strip(".").strip()
    if not host:
        return False
    for suf in OFFICIAL_HOST_SUFFIXES:
        suf = suf.lower().lstrip(".")
        if host == suf or host.endswith("." + suf):
            return True
    return False


def is_allowed_url(url: str) -> bool:
    """HTTPS only, official host suffix only."""
    if not url or not isinstance(url, str):
        return False
    raw = url.strip()
    try:
        u = urlparse(raw)
    except Exception:
        return False
    if u.scheme.lower() != "https":
        return False
    if any(x in (u.hostname or "").lower() for x in ("localhost", "example.com", "dummy", "placeholder")):
        return False
    return _host_allowed(u.hostname or "")


def assert_allowed_url(url: str) -> str:
    raw = (url or "").strip()
    if not is_allowed_url(raw):
        raise ValueError(
            "URL must be HTTPS on an allowlisted official domain "
            "(visa.com, visa.com.vn, issuer sites, …)."
        )
    return raw
