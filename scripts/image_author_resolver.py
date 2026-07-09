#!/usr/bin/env python3
"""
Image Author Resolver for Review Chân Thật.

Resolve photographer/creator attribution from trusted sources only.
Never invent, hardcode, or guess creators from slug/title/filename/query.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs, unquote

import frontmatter
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "posts"
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
MANIFEST_PATH = DATA_DIR / "images.json"
SOURCE_CACHE_PATH = DATA_DIR / "image-source-cache.json"
ATTR_CACHE_PATH = DATA_DIR / "image-attribution-cache.json"
DEFAULT_REPORT_JSON = REPORTS_DIR / "image-attribution-report.json"
DEFAULT_REPORT_MD = REPORTS_DIR / "image-attribution-report.md"

TZ_VN = timezone(timedelta(hours=7))
CACHE_TTL_DAYS = 30
REQUEST_TIMEOUT = 10
USER_AGENT = (
    "ReviewChanThatBot/1.0 (+https://banhang-chogao.github.io/reviewchanthat/; "
    "image-attribution-resolver)"
)

# Generic / platform / placeholder names — never treat as real creators
BLOCKED_CREATORS = {
    "unknown",
    "anonymous",
    "photographer",
    "creator",
    "author",
    "admin",
    "ai",
    "generated",
    "placeholder",
    "pexels",
    "pixabay",
    "unsplash",
    "freepik",
    "wikimedia",
    "wikimedia commons",
    "commons",
    "review chân thật",
    "review chan that",
    "n/a",
    "na",
    "none",
    "null",
    "undefined",
    "stock photo",
    "stock",
    "getty",
    "shutterstock",
    "park bogum",
    "park bo-gum",
    "park bo gum",
    "bae suzy",
    "iu",
    "yoo jaesuk",
    "choi wooshik",
    "lee minho",
    "lee min ho",
    "kim soo hyun",
    "song hye kyo",
}

BLOCKED_PHRASES = (
    "unknown photographer",
    "photographer unknown",
    "unknown creator",
    "creator unknown",
    "stock image",
)

PROVIDER_LICENSE = {
    "pexels": ("Pexels License", "https://www.pexels.com/license/"),
    "pixabay": ("Pixabay Content License", "https://pixabay.com/service/license-summary/"),
    "unsplash": ("Unsplash License", "https://unsplash.com/license"),
    "wikimedia": ("", ""),
    "freepik": ("Freepik License", "https://www.freepik.com/legal/terms-of-use"),
}

PROVIDER_DISPLAY = {
    "pexels": "Pexels",
    "pixabay": "Pixabay",
    "unsplash": "Unsplash",
    "wikimedia": "Wikimedia Commons",
    "freepik": "Freepik",
}


def now_iso() -> str:
    return datetime.now(TZ_VN).replace(microsecond=0).isoformat()


def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value).strip()
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def norm(value: Any) -> str:
    return " ".join(clean(value).casefold().split())


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def is_blocked_creator(name: str) -> bool:
    n = norm(name)
    if not n:
        return True
    if n in BLOCKED_CREATORS:
        return True
    if any(p in n for p in BLOCKED_PHRASES):
        return True
    return False


def looks_like_person_name(name: str) -> bool:
    """Accept concrete person/account names; reject empty/platform/generic."""
    name = clean(name)
    if not name or is_blocked_creator(name):
        return False
    if len(name) < 2:
        return False
    # Reject pure URLs
    if name.startswith("http://") or name.startswith("https://"):
        return False
    return True


def detect_provider(source_url: str, image_url: str = "", platform: str = "") -> str:
    blob = " ".join([clean(platform), clean(source_url), clean(image_url)]).lower()
    if "pexels.com" in blob:
        return "pexels"
    if "pixabay.com" in blob:
        return "pixabay"
    if "unsplash.com" in blob or "images.unsplash.com" in blob:
        return "unsplash"
    if "wikimedia.org" in blob or "wikipedia.org" in blob:
        return "wikimedia"
    if "freepik.com" in blob:
        return "freepik"
    p = norm(platform)
    for key in PROVIDER_DISPLAY:
        if key in p or PROVIDER_DISPLAY[key].lower() in p:
            return key
    return ""


def cache_key(provider: str, source_url: str, image_url: str) -> str:
    raw = f"{clean(provider)}|{clean(source_url)}|{clean(image_url)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cache_valid(entry: dict, refresh: bool) -> bool:
    if refresh or not entry:
        return False
    checked = clean(entry.get("checked_at") or entry.get("image_attribution_checked_at"))
    if not checked:
        return False
    try:
        ts = datetime.fromisoformat(checked)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=TZ_VN)
    except ValueError:
        return False
    return datetime.now(TZ_VN) - ts < timedelta(days=CACHE_TTL_DAYS)


class HttpClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._last_call: dict[str, float] = {}

    def _throttle(self, host: str, min_interval: float = 0.25) -> None:
        now = time.time()
        last = self._last_call.get(host, 0.0)
        wait = min_interval - (now - last)
        if wait > 0:
            time.sleep(wait)
        self._last_call[host] = time.time()

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    )
    def get(
        self,
        url: str,
        *,
        headers: dict | None = None,
        params: dict | None = None,
        min_interval: float = 0.25,
    ) -> requests.Response:
        host = urlparse(url).netloc or "default"
        self._throttle(host, min_interval)
        return self.session.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)


def empty_result(
    *,
    provider: str = "",
    source_url: str = "",
    error: str = "Provider/source page did not expose verified creator metadata",
    source: str = "not_found",
) -> dict[str, Any]:
    lic, lic_url = PROVIDER_LICENSE.get(provider, ("", ""))
    return {
        "image_creator": "",
        "image_creator_url": "",
        "image_creator_id": "",
        "image_provider": provider,
        "image_source": PROVIDER_DISPLAY.get(provider, provider.title() if provider else ""),
        "image_source_url": source_url,
        "image_license": lic,
        "image_license_url": lic_url,
        "image_attribution_verified": False,
        "image_attribution_source": source,
        "image_attribution_error": error,
        "image_attribution_checked_at": now_iso(),
        "confidence": "none",
        "raw_provider": None,
    }


def verified_result(
    *,
    creator: str,
    creator_url: str = "",
    creator_id: str = "",
    provider: str,
    source_url: str,
    license_name: str = "",
    license_url: str = "",
    attribution_source: str,
    confidence: str = "high",
    raw: Any = None,
) -> dict[str, Any]:
    if not looks_like_person_name(creator):
        return empty_result(
            provider=provider,
            source_url=source_url,
            error=f"Creator rejected as generic/platform name: {creator!r}",
            source="rejected_generic",
        )
    default_lic, default_lic_url = PROVIDER_LICENSE.get(provider, ("", ""))
    return {
        "image_creator": clean(creator),
        "image_creator_url": clean(creator_url),
        "image_creator_id": clean(creator_id),
        "image_provider": provider,
        "image_source": PROVIDER_DISPLAY.get(provider, provider.title()),
        "image_source_url": clean(source_url),
        "image_license": clean(license_name) or default_lic,
        "image_license_url": clean(license_url) or default_lic_url,
        "image_attribution_verified": True,
        "image_attribution_source": attribution_source,
        "image_attribution_error": "",
        "image_attribution_checked_at": now_iso(),
        "confidence": confidence,
        "raw_provider": raw,
    }


# --- ID parsers ---

# Accept both /photo/slug-name-123/ and /photo/123/
PEXELS_PAGE_RE = re.compile(r"pexels\.com/photo/(?:[^/]*?-)?(\d+)/?", re.I)
PEXELS_CDN_RE = re.compile(r"images\.pexels\.com/photos/(\d+)/", re.I)
# Accept /photos/, /vi/photos/, slug-id and bare id forms
PIXABAY_PAGE_RE = re.compile(
    r"pixabay\.com/(?:[a-z]{2}/)?(?:photos|illustrations|vectors)/(?:[^/]*?-)?(\d+)/?",
    re.I,
)
UNSPLASH_PAGE_RE = re.compile(r"unsplash\.com/photos/(?:[\w-]+-)?([A-Za-z0-9_-]{6,})", re.I)
WIKI_FILE_RE = re.compile(r"(?:File:|wiki/File:)([^?#]+)", re.I)
WIKI_UPLOAD_RE = re.compile(
    r"upload\.wikimedia\.org/wikipedia/commons/[0-9a-f]/[0-9a-f]{2}/([^/?#]+)", re.I
)


def parse_pexels_id(url: str) -> str:
    for rx in (PEXELS_PAGE_RE, PEXELS_CDN_RE):
        m = rx.search(url or "")
        if m:
            return m.group(1)
    return ""


def parse_pixabay_id(url: str) -> str:
    m = PIXABAY_PAGE_RE.search(url or "")
    return m.group(1) if m else ""


def parse_unsplash_id(url: str) -> str:
    m = UNSPLASH_PAGE_RE.search(url or "")
    if m:
        return m.group(1)
    # ixid sometimes embeds photo id; do not guess without clear page id
    return ""


def parse_wikimedia_title(url: str) -> str:
    url = url or ""
    m = WIKI_FILE_RE.search(url)
    if m:
        return unquote(m.group(1).replace("_", " "))
    m = WIKI_UPLOAD_RE.search(url)
    if m:
        return unquote(m.group(1))
    return ""


# --- Provider resolvers ---


def resolve_pexels_api(client: HttpClient, photo_id: str, source_url: str) -> dict | None:
    key = os.environ.get("PEXELS_API_KEY", "")
    if not key or not photo_id:
        return None
    try:
        resp = client.get(
            f"https://api.pexels.com/v1/photos/{photo_id}",
            headers={"Authorization": key},
            min_interval=0.35,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        creator = clean(data.get("photographer"))
        creator_url = clean(data.get("photographer_url"))
        creator_id = clean(data.get("photographer_id"))
        page_url = clean(data.get("url")) or source_url
        return verified_result(
            creator=creator,
            creator_url=creator_url,
            creator_id=creator_id,
            provider="pexels",
            source_url=page_url,
            attribution_source="pexels_api",
            raw={"id": data.get("id"), "photographer": creator, "photographer_id": creator_id},
        )
    except Exception:
        return None


def resolve_pixabay_api(client: HttpClient, photo_id: str, source_url: str) -> dict | None:
    key = os.environ.get("PIXABAY_API_KEY", "")
    if not key or not photo_id:
        return None
    try:
        resp = client.get(
            "https://pixabay.com/api/",
            params={"key": key, "id": photo_id},
            min_interval=0.4,
        )
        if resp.status_code != 200:
            return None
        hits = resp.json().get("hits") or []
        if not hits:
            return None
        hit = hits[0]
        user = clean(hit.get("user"))
        user_id = clean(hit.get("user_id"))
        page = clean(hit.get("pageURL")) or source_url
        profile = ""
        if user and user_id:
            # Pixabay profile slug is username-userid
            slug_user = user.replace(" ", "")
            profile = f"https://pixabay.com/users/{slug_user}-{user_id}/"
        return verified_result(
            creator=user,
            creator_url=profile,
            creator_id=user_id,
            provider="pixabay",
            source_url=page,
            attribution_source="pixabay_api",
            raw={"id": hit.get("id"), "user": user, "user_id": user_id},
        )
    except Exception:
        return None


def resolve_unsplash_api(client: HttpClient, photo_id: str, source_url: str) -> dict | None:
    key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    if not key or not photo_id:
        return None
    try:
        resp = client.get(
            f"https://api.unsplash.com/photos/{photo_id}",
            headers={"Authorization": f"Client-ID {key}"},
            min_interval=0.5,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        user = data.get("user") or {}
        user_links = user.get("links") or {}
        links = data.get("links") or {}
        creator = clean(user.get("name"))
        creator_url = clean(user_links.get("html"))
        creator_id = clean(user.get("id"))
        page = clean(links.get("html")) or source_url
        return verified_result(
            creator=creator,
            creator_url=creator_url,
            creator_id=creator_id,
            provider="unsplash",
            source_url=page,
            attribution_source="unsplash_api",
            raw={"id": data.get("id"), "user": {"name": creator, "id": creator_id}},
        )
    except Exception:
        return None


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return " ".join(text.split())


def resolve_wikimedia(client: HttpClient, title: str, source_url: str) -> dict | None:
    if not title:
        return None
    if not title.startswith("File:"):
        title = f"File:{title}"
    try:
        resp = client.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "prop": "imageinfo",
                "titles": title,
                "iiprop": "url|user|extmetadata",
                "iiextmetadatafilter": "Artist|Credit|Attribution|LicenseShortName|LicenseUrl|UsageTerms",
            },
            min_interval=0.4,
        )
        if resp.status_code != 200:
            return None
        pages = (resp.json().get("query") or {}).get("pages") or {}
        for page in pages.values():
            infos = page.get("imageinfo") or []
            if not infos:
                continue
            info = infos[0]
            ext = info.get("extmetadata") or {}

            def ext_val(key: str) -> str:
                node = ext.get(key) or {}
                return _strip_html(clean(node.get("value")))

            creator = ""
            for key in ("Attribution", "Artist", "Credit"):
                val = ext_val(key)
                if looks_like_person_name(val):
                    creator = val
                    break
            # Fallback to uploader only if no artist/credit — do NOT mark verified photographer
            uploader = clean(info.get("user"))
            if creator:
                return verified_result(
                    creator=creator,
                    creator_url="",
                    creator_id="",
                    provider="wikimedia",
                    source_url=source_url or clean(info.get("descriptionurl")),
                    license_name=ext_val("LicenseShortName"),
                    license_url=ext_val("LicenseUrl"),
                    attribution_source="wikimedia_extmetadata",
                    raw={"title": title, "uploader": uploader, "artist": creator},
                )
            return empty_result(
                provider="wikimedia",
                source_url=source_url,
                error="Wikimedia has uploader but no Artist/Credit/Attribution",
                source="wikimedia_uploader_only",
            )
    except Exception:
        return None
    return None


def extract_name_from_jsonld_node(node: Any) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return clean(node)
    if isinstance(node, list):
        for item in node:
            name = extract_name_from_jsonld_node(item)
            if name:
                return name
        return ""
    if isinstance(node, dict):
        for key in ("name", "alternateName"):
            if key in node:
                return clean(node.get(key))
        # nested person
        for key in ("author", "creator", "copyrightHolder"):
            if key in node:
                return extract_name_from_jsonld_node(node.get(key))
    return ""


def resolve_source_page(client: HttpClient, source_url: str, provider: str) -> dict | None:
    if not source_url or not source_url.startswith("http"):
        return None
    try:
        resp = client.get(source_url, min_interval=0.5)
        if resp.status_code != 200:
            return None
        html = resp.text
    except Exception:
        return None

    # JSON-LD
    try:
        import extruct
        from w3lib.html import get_base_url

        base = get_base_url(html, source_url)
        data = extruct.extract(
            html,
            base_url=base,
            syntaxes=["json-ld", "opengraph", "microdata"],
            uniform=True,
        )
    except Exception:
        data = {"json-ld": [], "opengraph": [], "microdata": []}
        # manual JSON-LD scrape
        for m in re.finditer(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            re.I | re.S,
        ):
            try:
                payload = json.loads(m.group(1))
                if isinstance(payload, list):
                    data["json-ld"].extend(payload)
                else:
                    data["json-ld"].append(payload)
            except Exception:
                continue

    for item in data.get("json-ld") or []:
        if not isinstance(item, dict):
            continue
        types = item.get("@type") or item.get("type") or ""
        type_str = " ".join(types) if isinstance(types, list) else str(types)
        candidates = []
        for key in ("author", "creator", "copyrightHolder", "creditText"):
            if key in item:
                candidates.append(extract_name_from_jsonld_node(item.get(key)))
        # ImageObject nesting
        if "ImageObject" in type_str or "image" in type_str.lower():
            pass
        for name in candidates:
            if looks_like_person_name(name):
                lic = clean(item.get("license") if isinstance(item.get("license"), str) else "")
                return verified_result(
                    creator=name,
                    creator_url="",
                    provider=provider,
                    source_url=source_url,
                    license_name=lic,
                    attribution_source="source_page_jsonld",
                    confidence="medium",
                )

    # Meta tags via BeautifulSoup
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        meta_keys = [
            ("property", "article:author"),
            ("name", "author"),
            ("name", "creator"),
            ("name", "copyright"),
            ("name", "twitter:creator"),
            ("property", "og:article:author"),
        ]
        for attr, key in meta_keys:
            tag = soup.find("meta", attrs={attr: key})
            if not tag:
                continue
            content = clean(tag.get("content"))
            if content.startswith("@"):
                content = content[1:]
            if looks_like_person_name(content):
                return verified_result(
                    creator=content,
                    provider=provider,
                    source_url=source_url,
                    attribution_source="source_page_meta",
                    confidence="medium",
                )
    except Exception:
        pass

    # Provider HTML fallbacks
    if provider == "pexels":
        m = re.search(r'href="(https?://www\.pexels\.com/@[^"]+)"[^>]*>\s*([^<]{2,80})\s*<', html)
        if m:
            url, name = clean(m.group(1)), clean(m.group(2))
            if looks_like_person_name(name):
                return verified_result(
                    creator=name,
                    creator_url=url,
                    provider="pexels",
                    source_url=source_url,
                    attribution_source="pexels_html",
                    confidence="medium",
                )
        m = re.search(r'"photographer"\s*:\s*"([^"]+)"', html)
        m2 = re.search(r'"photographer_url"\s*:\s*"([^"]+)"', html)
        if m:
            name = clean(m.group(1).encode().decode("unicode_escape", errors="ignore"))
            url = clean(m2.group(1)) if m2 else ""
            if looks_like_person_name(name):
                return verified_result(
                    creator=name,
                    creator_url=url,
                    provider="pexels",
                    source_url=source_url,
                    attribution_source="pexels_html",
                    confidence="medium",
                )

    if provider == "pixabay":
        m = re.search(r'href="(https?://pixabay\.com/users/([a-zA-Z0-9_]+)-(\d+)/?)"', html)
        if m:
            profile, user, uid = m.group(1), m.group(2), m.group(3)
            # Try nearby text for display name — use username if person-like
            if looks_like_person_name(user):
                return verified_result(
                    creator=user,
                    creator_url=profile,
                    creator_id=uid,
                    provider="pixabay",
                    source_url=source_url,
                    attribution_source="pixabay_html",
                    confidence="medium",
                )

    if provider == "unsplash":
        m = re.search(
            r'"name"\s*:\s*"([^"]+)"[^}]{0,200}"links"\s*:\s*\{\s*"html"\s*:\s*"(https://unsplash\.com/@[^"]+)"',
            html,
        )
        if m:
            name, url = clean(m.group(1)), clean(m.group(2))
            if looks_like_person_name(name):
                return verified_result(
                    creator=name,
                    creator_url=url,
                    provider="unsplash",
                    source_url=source_url,
                    attribution_source="unsplash_html",
                    confidence="medium",
                )

    return None


def resolve_embedded_metadata(local_path: str, provider: str, source_url: str) -> dict | None:
    if not local_path:
        return None
    path = Path(local_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        # try static paths
        alt = ROOT / "static" / local_path.lstrip("/")
        if alt.exists():
            path = alt
        else:
            return None

    names: list[str] = []
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        img = Image.open(path)
        exif = img.getexif() or {}
        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag in ("Artist", "Copyright", "XPAuthor") and value:
                names.append(clean(str(value)))
        # piexif
        try:
            import piexif

            raw = img.info.get("exif")
            if raw:
                exif_dict = piexif.load(raw)
                artist = exif_dict.get("0th", {}).get(piexif.ImageIFD.Artist)
                if artist:
                    if isinstance(artist, bytes):
                        artist = artist.decode("utf-8", errors="ignore")
                    names.append(clean(artist))
        except Exception:
            pass
    except Exception:
        pass

    try:
        import iptcinfo3

        info = iptcinfo3.IPTCInfo(str(path), force=True)
        for key in ("by-line", "credit", "copyright notice", "source"):
            val = info[key]
            if val:
                if isinstance(val, (list, tuple)):
                    val = " ".join(str(x) for x in val)
                names.append(clean(str(val)))
    except Exception:
        pass

    for name in names:
        # strip copyright symbols
        name = re.sub(r"^[©©️]\s*", "", name).strip()
        name = re.sub(r"^\d{4}\s+", "", name).strip()
        if looks_like_person_name(name):
            return verified_result(
                creator=name,
                provider=provider,
                source_url=source_url,
                attribution_source="embedded_exif_iptc_xmp",
                confidence="low",
            )
    return None


def resolve_from_manifest_raw(entry: dict, provider: str, source_url: str) -> dict | None:
    """Use stored raw provider API metadata if present and trustworthy."""
    raw = entry.get("raw_provider") or entry.get("provider_raw") or entry.get("api_response")
    if not isinstance(raw, dict):
        # Flat fields from select_images that came from API
        creator = clean(entry.get("creator"))
        creator_url = clean(entry.get("creator_url"))
        creator_id = clean(entry.get("creator_id") or entry.get("photographer_id") or entry.get("user_id"))
        # Only trust if provider matches and creator is not blocked
        if creator and looks_like_person_name(creator) and entry.get("source_platform"):
            # Require that this came from an API-backed selection pipeline.
            # We mark as verified only when we have a real creator from provider fields.
            # Prefer re-fetching via API when keys exist; this path is fallback.
            has_api_hint = bool(
                entry.get("provider_used")
                or entry.get("photographer_id")
                or entry.get("user_id")
                or entry.get("photo_id")
                or entry.get("image_id")
            )
            if has_api_hint and provider in ("pexels", "pixabay", "unsplash", "freepik"):
                # Without re-calling API we still accept API-sourced manifest creator
                # only if creator looks real AND we will prefer live API above this.
                return verified_result(
                    creator=creator,
                    creator_url=creator_url,
                    creator_id=creator_id,
                    provider=provider,
                    source_url=source_url or clean(entry.get("source_url")),
                    attribution_source=f"{provider}_manifest",
                    confidence="medium",
                    raw={"from": "manifest", "creator": creator},
                )
    else:
        if provider == "pexels":
            creator = clean(raw.get("photographer"))
            if looks_like_person_name(creator):
                return verified_result(
                    creator=creator,
                    creator_url=clean(raw.get("photographer_url")),
                    creator_id=clean(raw.get("photographer_id")),
                    provider="pexels",
                    source_url=clean(raw.get("url")) or source_url,
                    attribution_source="pexels_api",
                    raw=raw,
                )
        if provider == "pixabay":
            user = clean(raw.get("user"))
            uid = clean(raw.get("user_id"))
            if looks_like_person_name(user):
                profile = f"https://pixabay.com/users/{user.replace(' ', '')}-{uid}/" if uid else ""
                return verified_result(
                    creator=user,
                    creator_url=profile,
                    creator_id=uid,
                    provider="pixabay",
                    source_url=clean(raw.get("pageURL")) or source_url,
                    attribution_source="pixabay_api",
                    raw=raw,
                )
        if provider == "unsplash":
            user = raw.get("user") or {}
            name = clean(user.get("name"))
            links = (user.get("links") or {})
            if looks_like_person_name(name):
                return verified_result(
                    creator=name,
                    creator_url=clean(links.get("html")),
                    creator_id=clean(user.get("id")),
                    provider="unsplash",
                    source_url=source_url,
                    attribution_source="unsplash_api",
                    raw=raw,
                )
    return None


def resolve_attribution(
    client: HttpClient,
    *,
    source_url: str,
    image_url: str = "",
    platform: str = "",
    local_path: str = "",
    manifest_entry: dict | None = None,
    attr_cache: dict | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    provider = detect_provider(source_url, image_url, platform)
    key = cache_key(provider, source_url, image_url)
    attr_cache = attr_cache if attr_cache is not None else {}
    cached = attr_cache.get(key)
    if isinstance(cached, dict) and cache_valid(cached, refresh):
        out = dict(cached)
        out["from_cache"] = True
        return out

    errors: list[str] = []

    # 1) Live provider API by id (highest trust)
    def _cache_and_return(result: dict) -> dict:
        attr_cache[key] = {k: v for k, v in result.items() if k != "raw_provider"}
        attr_cache[key]["checked_at"] = result["image_attribution_checked_at"]
        result["from_cache"] = False
        return result

    if provider == "pexels":
        pid = parse_pexels_id(source_url) or parse_pexels_id(image_url)
        if pid:
            if os.environ.get("PEXELS_API_KEY"):
                result = resolve_pexels_api(client, pid, source_url)
                if result and result.get("image_attribution_verified"):
                    return _cache_and_return(result)
                if result and result.get("image_attribution_source") == "rejected_generic":
                    # API returned a platform/generic name — do not invent fallback
                    return _cache_and_return(result)
                errors.append(f"pexels_api_miss id={pid}")
            else:
                errors.append("PEXELS_API_KEY missing")

    if provider == "pixabay":
        pid = parse_pixabay_id(source_url) or parse_pixabay_id(image_url)
        if pid:
            if os.environ.get("PIXABAY_API_KEY"):
                result = resolve_pixabay_api(client, pid, source_url)
                if result and result.get("image_attribution_verified"):
                    return _cache_and_return(result)
                if result and result.get("image_attribution_source") == "rejected_generic":
                    return _cache_and_return(result)
                errors.append(f"pixabay_api_miss id={pid}")
            else:
                errors.append("PIXABAY_API_KEY missing")

    if provider == "unsplash":
        pid = parse_unsplash_id(source_url)
        if pid:
            if os.environ.get("UNSPLASH_ACCESS_KEY"):
                result = resolve_unsplash_api(client, pid, source_url)
                if result and result.get("image_attribution_verified"):
                    return _cache_and_return(result)
                if result and result.get("image_attribution_source") == "rejected_generic":
                    return _cache_and_return(result)
                errors.append(f"unsplash_api_miss id={pid}")
            else:
                errors.append("UNSPLASH_ACCESS_KEY missing")

    if provider == "wikimedia":
        title = parse_wikimedia_title(source_url) or parse_wikimedia_title(image_url)
        result = resolve_wikimedia(client, title, source_url)
        if result and result.get("image_attribution_verified"):
            return _cache_and_return(result)
        if result:
            errors.append(result.get("image_attribution_error") or "wikimedia_no_artist")

    # 1b) Manifest raw (secondary — only after live API attempt)
    if manifest_entry:
        result = resolve_from_manifest_raw(manifest_entry, provider, source_url)
        if result and result.get("image_attribution_verified"):
            # If live API was available we already tried; accept manifest as medium
            attr_cache[key] = {k: v for k, v in result.items() if k != "raw_provider"}
            attr_cache[key]["checked_at"] = result["image_attribution_checked_at"]
            result["from_cache"] = False
            return result

    # 2–3) Source page structured data / HTML
    result = resolve_source_page(client, source_url, provider)
    if result and result.get("image_attribution_verified"):
        attr_cache[key] = {k: v for k, v in result.items() if k != "raw_provider"}
        attr_cache[key]["checked_at"] = result["image_attribution_checked_at"]
        result["from_cache"] = False
        return result
    errors.append("source_page_no_creator")

    # 4) Embedded metadata
    result = resolve_embedded_metadata(local_path, provider, source_url)
    if result and result.get("image_attribution_verified"):
        attr_cache[key] = {k: v for k, v in result.items() if k != "raw_provider"}
        attr_cache[key]["checked_at"] = result["image_attribution_checked_at"]
        result["from_cache"] = False
        return result
    errors.append("embedded_meta_no_creator")

    # 5) Reverse lookup already covered via CDN id parsers above

    out = empty_result(
        provider=provider,
        source_url=source_url,
        error="; ".join(errors) if errors else "not_found",
        source="not_found",
    )
    attr_cache[key] = {k: v for k, v in out.items() if k != "raw_provider"}
    attr_cache[key]["checked_at"] = out["image_attribution_checked_at"]
    out["from_cache"] = False
    return out


# --- Front matter helpers (preserve dates / body) ---

def split_front_matter(text: str):
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None, None, None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return lines[:1], lines[1:idx], lines[idx:]
    return None, None, None


def yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return '""'
    if isinstance(value, (int, float)):
        return str(value)
    value = clean(value)
    if not value:
        return '""'
    if re.search(r'[:#\[\]{}&*!|>\'"%@`]|^\s|\s$|^[-?]', value) or "\n" in value:
        return json.dumps(value, ensure_ascii=False)
    return value


def set_scalar(lines: list[str], key: str, value: Any) -> bool:
    rendered = f"{key}: {yaml_scalar(value)}\n"
    pattern = re.compile(rf"^{re.escape(key)}:\s*")
    for idx, line in enumerate(lines):
        if pattern.match(line):
            if line != rendered:
                lines[idx] = rendered
                return True
            return False
    # Insert near image block
    anchors = [
        "image_attribution_checked_at",
        "image_attribution_error",
        "image_attribution_source",
        "image_attribution_verified",
        "image_creator_id",
        "image_creator_url",
        "image_creator",
        "image_license_url",
        "image_license",
        "image_provider",
        "image_owner",
        "image_commercial_use",
        "image_source_url",
        "image_source",
        "thumbnail",
        "image",
    ]
    insert_at = len(lines)
    for anchor in anchors:
        ap = re.compile(rf"^{re.escape(anchor)}:\s*")
        for idx, line in enumerate(lines):
            if ap.match(line):
                insert_at = idx + 1
                lines.insert(insert_at, rendered)
                return True
    lines.insert(insert_at, rendered)
    return True


def apply_result_to_front_matter(path: Path, result: dict) -> tuple[bool, str]:
    original = path.read_text(encoding="utf-8")
    prefix, front_lines, suffix = split_front_matter(original)
    if front_lines is None:
        return False, "no_front_matter"

    # Clear fake / unverified creators before applying
    fields = {
        "image_provider": result.get("image_provider") or "",
        "image_source": result.get("image_source") or "",
        "image_source_url": result.get("image_source_url") or "",
        "image_creator": result.get("image_creator") or "",
        "image_creator_url": result.get("image_creator_url") or "",
        "image_creator_id": result.get("image_creator_id") or "",
        "image_license": result.get("image_license") or "",
        "image_license_url": result.get("image_license_url") or "",
        "image_attribution_verified": bool(result.get("image_attribution_verified")),
        "image_attribution_source": result.get("image_attribution_source") or "not_found",
        "image_attribution_checked_at": result.get("image_attribution_checked_at") or now_iso(),
    }
    if not fields["image_attribution_verified"]:
        fields["image_creator"] = ""
        fields["image_creator_url"] = ""
        fields["image_creator_id"] = ""
        fields["image_attribution_error"] = result.get("image_attribution_error") or (
            "Provider/source page did not expose verified creator metadata"
        )
    else:
        # remove error field if present
        for idx, line in enumerate(list(front_lines)):
            if line.startswith("image_attribution_error:"):
                del front_lines[idx]
                break

    # Ensure image paths never start with /
    for path_key in ("image", "thumbnail"):
        p = re.compile(rf"^{path_key}:\s*(.*)$")
        for idx, line in enumerate(front_lines):
            m = p.match(line.rstrip("\n"))
            if m:
                val = m.group(1).strip().strip('"').strip("'")
                if val.startswith("/"):
                    set_scalar(front_lines, path_key, val.lstrip("/"))

    changed = False
    for k, v in fields.items():
        if set_scalar(front_lines, k, v):
            changed = True

    if not fields["image_attribution_verified"]:
        if set_scalar(front_lines, "image_attribution_error", fields.get("image_attribution_error", "")):
            changed = True

    if changed:
        path.write_text("".join(prefix + front_lines + suffix), encoding="utf-8")
        return True, "updated"
    return False, "unchanged"


def load_posts(post_path: str | None = None) -> list[Path]:
    if post_path:
        p = Path(post_path)
        if not p.is_absolute():
            p = ROOT / p
        return [p]
    return sorted(CONTENT_DIR.glob("*.md"))


def build_manifest_index(manifest: dict) -> dict[str, dict]:
    out = {}
    for entry in manifest.get("posts") or []:
        slug = clean(entry.get("slug"))
        if slug:
            out[slug] = entry
    return out


def update_manifest_entry(entry: dict, result: dict) -> None:
    creator = result.get("image_creator") or ""
    verified = bool(result.get("image_attribution_verified"))
    entry["creator"] = creator if verified else ""
    entry["creator_url"] = (result.get("image_creator_url") or "") if verified else ""
    entry["creator_id"] = (result.get("image_creator_id") or "") if verified else ""
    entry["attribution_verified"] = verified
    entry["attribution_source"] = result.get("image_attribution_source") or "not_found"
    entry["attribution_checked_at"] = result.get("image_attribution_checked_at") or now_iso()
    platform = result.get("image_source") or entry.get("source_platform") or ""
    entry["watermark_text"] = (
        f"Source: {platform} / {creator}" if verified and creator else f"Source: {platform}" if platform else ""
    )
    if result.get("raw_provider"):
        entry["raw_provider"] = result["raw_provider"]
    if result.get("image_provider"):
        entry["image_provider"] = result["image_provider"]


def write_reports(rows: list[dict], path_json: Path, path_md: Path) -> None:
    verified = sum(1 for r in rows if r.get("verified"))
    missing = sum(1 for r in rows if not r.get("verified"))
    cleared = sum(1 for r in rows if r.get("cleared_fake"))
    report = {
        "generated_at": now_iso(),
        "summary": {
            "total_scanned": len(rows),
            "verified_creator": verified,
            "not_found": missing,
            "cleared_fake_or_unverified": cleared,
        },
        "posts": rows,
    }
    save_json(path_json, report)

    lines = [
        "# Image Attribution Report",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Total scanned: **{len(rows)}**",
        f"- Verified creator: **{verified}**",
        f"- Not found / empty: **{missing}**",
        f"- Cleared fake/unverified: **{cleared}**",
        "",
        "| slug | provider | verified | creator | source | confidence | error |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            "| {slug} | {provider} | {verified} | {creator} | {method} | {confidence} | {error} |".format(
                slug=r.get("slug", ""),
                provider=r.get("provider", ""),
                verified="yes" if r.get("verified") else "no",
                creator=(r.get("creator") or "").replace("|", "/"),
                method=r.get("resolver_method", ""),
                confidence=r.get("confidence", ""),
                error=(r.get("error") or "").replace("|", "/"),
            )
        )
    path_md.parent.mkdir(parents=True, exist_ok=True)
    path_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def process_post(
    path: Path,
    *,
    client: HttpClient,
    manifest_by_slug: dict,
    attr_cache: dict,
    refresh: bool,
    write: bool,
) -> dict:
    post = frontmatter.load(str(path))
    meta = post.metadata
    slug = clean(meta.get("slug")) or path.stem
    source_url = clean(meta.get("image_source_url"))
    image = clean(meta.get("image"))
    platform = clean(meta.get("image_provider") or meta.get("image_source"))
    old_creator = clean(meta.get("image_creator"))
    old_verified = meta.get("image_attribution_verified")

    manifest_entry = manifest_by_slug.get(slug) or {}
    image_url = clean(manifest_entry.get("direct_url")) or image
    local_path = clean(manifest_entry.get("local_source_path")) or (
        f"static/{image}" if image and not image.startswith("http") else ""
    )

    if not source_url and not image:
        return {
            "slug": slug,
            "path": str(path.relative_to(ROOT)),
            "provider": "",
            "source_url": "",
            "verified": False,
            "creator": "",
            "resolver_method": "skipped",
            "confidence": "none",
            "error": "no_image_metadata",
            "checked_at": now_iso(),
            "cleared_fake": False,
            "written": False,
        }

    result = resolve_attribution(
        client,
        source_url=source_url or clean(manifest_entry.get("source_url")),
        image_url=image_url,
        platform=platform or clean(manifest_entry.get("source_platform")),
        local_path=local_path,
        manifest_entry=manifest_entry or None,
        attr_cache=attr_cache,
        refresh=refresh,
    )

    cleared = False
    if old_creator and (
        is_blocked_creator(old_creator)
        or not result.get("image_attribution_verified")
        or clean(result.get("image_creator")) != old_creator
    ):
        if old_creator and not result.get("image_attribution_verified"):
            cleared = True
        if old_creator and is_blocked_creator(old_creator):
            cleared = True

    written = False
    if write:
        changed, _ = apply_result_to_front_matter(path, result)
        written = changed
        if manifest_entry:
            update_manifest_entry(manifest_entry, result)

    return {
        "slug": slug,
        "path": str(path.relative_to(ROOT)),
        "provider": result.get("image_provider") or platform,
        "source_url": result.get("image_source_url") or source_url,
        "verified": bool(result.get("image_attribution_verified")),
        "creator": result.get("image_creator") or "",
        "creator_url": result.get("image_creator_url") or "",
        "resolver_method": result.get("image_attribution_source") or "not_found",
        "confidence": result.get("confidence") or "none",
        "error": result.get("image_attribution_error") or "",
        "checked_at": result.get("image_attribution_checked_at") or now_iso(),
        "from_cache": bool(result.get("from_cache")),
        "cleared_fake": cleared,
        "previous_creator": old_creator,
        "previous_verified": old_verified,
        "written": written,
    }


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Resolve verified image creator attribution")
    parser.add_argument("--post", help="Path to a single post markdown file")
    parser.add_argument("--all", action="store_true", help="Process all posts")
    parser.add_argument("--refresh", action="store_true", help="Ignore attribution cache")
    parser.add_argument("--write", action="store_true", help="Write front matter / caches")
    parser.add_argument("--dry-run", action="store_true", help="Do not write (default)")
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    args = parser.parse_args(argv)

    if not args.post and not args.all:
        # default: all dry-run
        args.all = True

    write = bool(args.write) and not args.dry_run
    # default dry-run if no --write
    if not args.write:
        write = False

    posts = load_posts(args.post)
    if not posts:
        print("No posts found")
        return 1

    manifest = load_json(MANIFEST_PATH, {"posts": []})
    manifest_by_slug = build_manifest_index(manifest)
    source_cache = load_json(SOURCE_CACHE_PATH, {})
    attr_cache = load_json(ATTR_CACHE_PATH, {})
    client = HttpClient()

    print("=== Image Author Resolver ===")
    print(f"  Posts: {len(posts)}")
    print(f"  Mode: {'WRITE' if write else 'DRY-RUN'}")
    print(f"  Refresh: {args.refresh}")
    print(f"  PEXELS_API_KEY: {'yes' if os.environ.get('PEXELS_API_KEY') else 'no'}")
    print(f"  PIXABAY_API_KEY: {'yes' if os.environ.get('PIXABAY_API_KEY') else 'no'}")
    print(f"  UNSPLASH_ACCESS_KEY: {'yes' if os.environ.get('UNSPLASH_ACCESS_KEY') else 'no'}")

    rows: list[dict] = []
    for path in posts:
        try:
            row = process_post(
                path,
                client=client,
                manifest_by_slug=manifest_by_slug,
                attr_cache=attr_cache,
                refresh=args.refresh,
                write=write,
            )
            rows.append(row)
            status = "VERIFIED" if row["verified"] else "NOT_FOUND"
            creator = row["creator"] or "—"
            print(f"  [{status}] {row['slug']}: {creator} ({row['resolver_method']})")
        except Exception as e:
            rows.append(
                {
                    "slug": path.stem,
                    "path": str(path),
                    "provider": "",
                    "source_url": "",
                    "verified": False,
                    "creator": "",
                    "resolver_method": "error",
                    "confidence": "none",
                    "error": str(e),
                    "checked_at": now_iso(),
                    "cleared_fake": False,
                    "written": False,
                }
            )
            print(f"  [ERROR] {path.name}: {e}")

    # Sync source cache from manifest
    if write:
        for slug, entry in manifest_by_slug.items():
            if slug in source_cache and isinstance(source_cache[slug], dict):
                update_manifest_entry(source_cache[slug], {
                    "image_creator": entry.get("creator", ""),
                    "image_creator_url": entry.get("creator_url", ""),
                    "image_creator_id": entry.get("creator_id", ""),
                    "image_attribution_verified": entry.get("attribution_verified", False),
                    "image_attribution_source": entry.get("attribution_source", "not_found"),
                    "image_attribution_checked_at": entry.get("attribution_checked_at", now_iso()),
                    "image_source": entry.get("source_platform", ""),
                    "raw_provider": entry.get("raw_provider"),
                    "image_provider": entry.get("image_provider", ""),
                })
            else:
                source_cache[slug] = entry
        save_json(MANIFEST_PATH, manifest)
        save_json(SOURCE_CACHE_PATH, source_cache)
        save_json(ATTR_CACHE_PATH, attr_cache)

    report_json = Path(args.report_json)
    report_md = Path(args.report_md)
    if not report_json.is_absolute():
        report_json = ROOT / report_json
    if not report_md.is_absolute():
        report_md = ROOT / report_md
    write_reports(rows, report_json, report_md)

    verified = sum(1 for r in rows if r.get("verified"))
    missing = sum(1 for r in rows if not r.get("verified"))
    cleared = sum(1 for r in rows if r.get("cleared_fake"))
    print("\n=== Summary ===")
    print(f"  Scanned: {len(rows)}")
    print(f"  Verified: {verified}")
    print(f"  Not found: {missing}")
    print(f"  Cleared fake/unverified: {cleared}")
    print(f"  Report JSON: {report_json}")
    print(f"  Report MD: {report_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
