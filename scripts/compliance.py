#!/usr/bin/env python3
"""
Content compliance checker for Review Chân Thật Hugo blog.

Usage:
  python scripts/compliance.py
  python scripts/compliance.py --check
  python scripts/compliance.py --fix
  python scripts/compliance.py --strict --report-json data/compliance-report.json
  python scripts/compliance.py --self-test
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

try:
    import frontmatter
except ImportError:
    print("python-frontmatter not installed. Run: pip install python-frontmatter")
    sys.exit(2)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from creator_policy import is_blocked_creator
from image_gate_policy import (
    gate_score_passes,
    is_meaningful_gate_score,
    is_self_owned_meta,
    normalize_gate_score,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIRS = [
    os.path.join(ROOT, "content", "posts"),
    os.path.join(ROOT, "content"),
]
MANIFEST_PATH = os.path.join(ROOT, "data", "images.json")
SOURCE_CACHE_PATH = os.path.join(ROOT, "data", "image-source-cache.json")
AUTHORS_PATH = os.path.join(ROOT, "data", "authors.json")
WHITELIST_PATH = os.path.join(ROOT, "data", "dupe-whitelist.json")
PUBLIC_DIR = os.path.join(ROOT, "public")
DEFAULT_REPORT = os.path.join(ROOT, "data", "compliance-report.json")

REQUIRED_FIELDS = ("title", "date", "description", "categories", "tags", "author", "image", "thumbnail")
IMAGE_REQUIRED = (
    "image_source",
    "image_source_url",
    "image_license",
    "image_commercial_use",
    "image_owner",
)
FALLBACK_MARKERS = ("fallback", "placeholder", "default", "generated", "navy")
DATE_PLACEHOLDERS = {"2025-01-01", "2026-01-01"}
ALLOWED_IMAGE_SOURCES = {"pexels", "pixabay", "unsplash", "freepik", "self", "self-owned"}
SOURCE_DOMAINS = {
    "pexels": ("pexels.com",),
    "pixabay": ("pixabay.com",),
    "unsplash": ("unsplash.com",),
    "freepik": ("freepik.com",),
}
ADSENSE_BLOCK = re.compile(
    r"\b(casino online|online casino|đánh bạc online|cờ bạc online|betting site|"
    r"ma túy|hack\s+account|crack\s+software|lừa đảo tiền)\b",
    re.I,
)
ADSENSE_WARN_TITLE = re.compile(
    r"\b(sốc|100%|chắc chắn giàu|đảm bảo|bí mật không ai nói)\b",
    re.I,
)
TONE_WARN = re.compile(
    r"\b(tuyệt vời nhất|đỉnh nhất|không thể bỏ lỡ|chắc chắn phải đi|đáng tiền 100%|"
    r"huyền thoại|siêu đẳng|best choice|hoàn hảo cho mọi người|không có nhược điểm|đảm bảo)\b",
    re.I,
)
CLAIM_STRONG = re.compile(
    r"\b(chính thức|xác nhận|quy định|bị phạt|visa|luật|y tế|tài chính|đầu tư|"
    r"apple đã xác nhận|trip\.com nói|chính phủ)\b",
    re.I,
)
CLAIM_CONTEXT = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d+\s*%|giá|lịch|hoạt động từ|hỗ trợ máy|theo)\b",
    re.I,
)
LEGAL_SENSITIVE = re.compile(r"\b(visa|luật|y tế|tài chính|đầu tư|bị phạt|quy định pháp)\b", re.I)
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
ATTRIBUTION_TAGS = re.compile(
    r"\[(Apple đã xác nhận|Phân tích|Phản hồi beta|Apple preview|Tin đồn|WWDC)\]",
    re.I,
)
NEGATED_CLAIM = re.compile(r"\bkhông\s+(đảm bảo|chắc chắn|100%)\b", re.I)
END_SECTION_HEADINGS = (
    "link nội bộ",
    "liên kết nội bộ",
    "liên kết bên trong",
    "nguồn tham khảo",
    "faq",
    "câu hỏi thường gặp",
    "bài viết liên quan",
    "đọc thêm",
)
BULLET_PREFIX_RE = re.compile(r"^[-•*]\s+")


@dataclass
class Issue:
    severity: str
    code: str
    file: str
    message: str
    suggestion: str = ""


@dataclass
class ComplianceReport:
    summary: dict[str, int] = field(default_factory=lambda: {
        "files_scanned": 0,
        "errors": 0,
        "warnings": 0,
        "fixed": 0,
    })
    issues: list[Issue] = field(default_factory=list)

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)
        if issue.severity == "ERROR":
            self.summary["errors"] += 1
        elif issue.severity == "WARN":
            self.summary["warnings"] += 1

    def add_fix(self) -> None:
        self.summary["fixed"] += 1


def clean_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def field_missing(meta: dict, field_name: str) -> bool:
    value = meta.get(field_name)
    if value is None:
        return True
    if isinstance(value, bool):
        return False
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return not clean_text(str(value))


def normalized(value: Any) -> str:
    return " ".join(clean_text(value).casefold().split())


def load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def dict_to_string(item: dict) -> str:
    if len(item) == 1:
        key, value = next(iter(item.items()))
        return f"{clean_text(str(key))}: {clean_text(str(value))}"
    return "; ".join(f"{clean_text(str(k))}: {clean_text(str(v))}" for k, v in item.items())


def parse_map_string(text: str) -> str | None:
    inner = text[4:-1].strip()
    if not inner:
        return None
    if ": " in inner:
        key, value = inner.split(": ", 1)
        return f"{clean_text(key)}: {clean_text(value)}"
    if ":" in inner:
        key, value = inner.rsplit(":", 1)
        return f"{clean_text(key)}: {clean_text(value)}"
    return None


def item_to_string(item: Any) -> str:
    if isinstance(item, str):
        text = item
    elif isinstance(item, dict):
        text = dict_to_string(item)
    elif isinstance(item, (list, tuple)):
        text = " ".join(part for part in (item_to_string(x) for x in item) if part)
    else:
        text = str(item)
    text = clean_text(text)
    if text.startswith("map[") and text.endswith("]"):
        parsed = parse_map_string(text)
        if parsed:
            return parsed
    text = BULLET_PREFIX_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_date(value: Any) -> datetime | None:
    text = clean_text(str(value))
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    for fmt in ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text[:19] if "%" in fmt and len(text) > 19 else text[:10] if fmt == "%Y-%m-%d" else text, fmt)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))


class ComplianceChecker:
    def __init__(self, fix: bool = False, strict: bool = False, scan_public: bool = True) -> None:
        self.fix = fix
        self.strict = strict
        self.scan_public = scan_public
        self.report = ComplianceReport()
        self.manifest_by_slug = self._load_manifest()
        self.cache_by_slug = self._load_cache()
        self.whitelist_urls = set(load_json(WHITELIST_PATH, {}).get("whitelisted_urls", []))
        self.posts_data: list[dict[str, Any]] = []
        self.image_paths: dict[str, list[str]] = {}
        self.source_urls: dict[str, list[str]] = {}

    def _load_manifest(self) -> dict[str, dict]:
        data = load_json(MANIFEST_PATH, {"posts": []})
        return {
            clean_text(entry.get("slug")): entry
            for entry in data.get("posts", [])
            if clean_text(entry.get("slug"))
        }

    def _load_cache(self) -> dict[str, dict]:
        data = load_json(SOURCE_CACHE_PATH, {})
        if isinstance(data, dict):
            return {clean_text(k): v for k, v in data.items() if isinstance(v, dict)}
        return {}

    def add_issue(self, severity: str, code: str, file: str, message: str, suggestion: str = "") -> None:
        if self.strict and severity == "WARN":
            severity = "ERROR"
        self.report.add(Issue(severity, code, file, message, suggestion))

    def discover_posts(self) -> list[str]:
        paths: list[str] = []
        posts_dir = os.path.join(ROOT, "content", "posts")
        if os.path.isdir(posts_dir):
            for fname in sorted(os.listdir(posts_dir)):
                if fname.endswith(".md"):
                    paths.append(os.path.join(posts_dir, fname))
        return paths

    def run(self) -> int:
        paths = self.discover_posts()
        self.report.summary["files_scanned"] = len(paths)
        for path in paths:
            self.scan_post(path)
        self.check_duplicates()
        if self.scan_public and os.path.isdir(PUBLIC_DIR):
            self.scan_public_artifacts()
        return 0 if self.report.summary["errors"] == 0 else 1

    def scan_post(self, path: str) -> None:
        rel = os.path.relpath(path, ROOT)
        try:
            with open(path, encoding="utf-8") as handle:
                post = frontmatter.load(handle)
        except Exception as exc:
            self.add_issue("ERROR", "FRONTMATTER_PARSE", rel, f"Cannot parse front matter: {exc}")
            return

        meta = post.metadata
        body = post.content or ""
        fname = os.path.basename(path)
        slug = clean_text(meta.get("slug")) or fname.replace(".md", "")

        if self.fix:
            changed = self.apply_safe_fixes(path, post, slug)
            if changed:
                with open(path, "w", encoding="utf-8") as handle:
                    frontmatter.dump(post, handle)
                self.report.add_fix()

        self.check_frontmatter(rel, meta, slug, fname)
        self.check_images(rel, meta, slug)
        self.check_image_creator(rel, meta, slug, fname)
        self.check_ai_summary(rel, meta)
        self.check_claim_sources(rel, meta, body)
        self.check_adsense(rel, meta, body)
        self.check_tone(rel, body)
        self.check_repeated_end_sections(rel, body)
        self.check_seo(rel, meta, slug)

        self.posts_data.append({
            "file": rel,
            "slug": slug,
            "title": clean_text(meta.get("title")),
            "description": clean_text(meta.get("description")),
            "body_start": body[:500],
            "tags": meta.get("tags") or [],
            "ai_summary": meta.get("ai_summary", {}).get("items", []) if meta.get("ai_summary") else [],
        })

        image = clean_text(meta.get("image"))
        source_url = clean_text(meta.get("image_source_url"))
        if image:
            self.image_paths.setdefault(image, []).append(rel)
        if source_url:
            self.source_urls.setdefault(source_url, []).append(rel)

    def apply_safe_fixes(self, path: str, post: Any, slug: str) -> bool:
        changed = False
        meta = post.metadata

        for key in ("image", "thumbnail"):
            val = clean_text(meta.get(key))
            if val.startswith("/"):
                candidate = val.lstrip("/")
                if os.path.exists(os.path.join(ROOT, "static", candidate)):
                    meta[key] = candidate
                    changed = True

        ai = meta.get("ai_summary")
        if isinstance(ai, dict) and ai.get("items"):
            normalized_items = []
            for item in ai["items"]:
                text = item_to_string(item)
                if text and "map[" not in text:
                    normalized_items.append(text)
            if normalized_items != ai.get("items"):
                ai["items"] = normalized_items
                meta["ai_summary"] = ai
                changed = True

        creator = clean_text(meta.get("image_creator"))
        if creator and not self._verified_creator(slug, creator):
            meta["image_creator"] = ""
            meta["image_creator_url"] = ""
            changed = True

        new_body, body_changed = self._strip_manual_end_sections(post.content or "")
        if body_changed:
            post.content = new_body
            changed = True
        return changed

    def _strip_manual_end_sections(self, body: str) -> tuple[str, bool]:
        lines = body.splitlines()
        if not lines:
            return body, False
        cutoff = None
        start_threshold = max(0, int(len(lines) * 0.5))
        for idx in range(start_threshold, len(lines)):
            line = lines[idx].strip().lower()
            if line.startswith("## "):
                heading = line[3:].strip()
                if heading in END_SECTION_HEADINGS:
                    cutoff = idx
                    break
        if cutoff is None:
            return body, False
        return "\n".join(lines[:cutoff]).rstrip() + "\n", True

    def check_frontmatter(self, rel: str, meta: dict, slug: str, fname: str) -> None:
        if meta.get("draft") is True:
            self.add_issue("ERROR", "DRAFT_POST", rel, "draft=true — post is not publishable")

        for field_name in REQUIRED_FIELDS:
            value = meta.get(field_name)
            if value is None or value == "" or value == []:
                self.add_issue("ERROR", "MISSING_FIELD", rel, f"Missing required field: {field_name}")

        title = clean_text(meta.get("title"))
        description = clean_text(meta.get("description"))
        if title and len(title) < 12:
            self.add_issue("ERROR", "TITLE_TOO_SHORT", rel, "Title is too short")
        if description and len(description) < 40:
            self.add_issue("WARN", "DESCRIPTION_TOO_SHORT", rel, "Description is short for SEO")

        for date_field in ("date", "lastmod", "updated"):
            raw = meta.get(date_field)
            if not raw:
                continue
            dt = parse_date(raw)
            if not dt:
                self.add_issue("ERROR", "INVALID_DATE", rel, f"{date_field} is not parseable: {raw}")
                continue
            day = dt.strftime("%Y-%m-%d")
            if day in DATE_PLACEHOLDERS or day.startswith("2099") or day.startswith("1970"):
                self.add_issue("ERROR", "PLACEHOLDER_DATE", rel, f"{date_field} looks like placeholder: {day}")
            now = datetime.now(timezone.utc)
            if dt.astimezone(timezone.utc) > now:
                self.add_issue("ERROR", "FUTURE_DATE", rel, f"{date_field} is in the future: {raw}")

        if slug and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            self.add_issue("WARN", "SLUG_NON_ASCII", rel, f"Slug may produce non-ASCII URL segment: {slug}")

    def check_images(self, rel: str, meta: dict, slug: str) -> None:
        image = clean_text(meta.get("image"))
        thumbnail = clean_text(meta.get("thumbnail"))
        expected = f"images/posts/{slug}.webp"

        for field_name, value in (("image", image), ("thumbnail", thumbnail)):
            if not value:
                continue
            if value.startswith("/"):
                self.add_issue("ERROR", "ABSOLUTE_IMAGE_PATH", rel, f"{field_name} must not start with /")
            low = value.lower()
            if any(marker in low for marker in FALLBACK_MARKERS):
                self.add_issue("ERROR", "FALLBACK_IMAGE", rel, f"{field_name} looks like fallback/placeholder: {value}")
            if not value.startswith("http"):
                local = os.path.join(ROOT, "static", value)
                if not os.path.exists(local):
                    self.add_issue("ERROR", "IMAGE_FILE_MISSING", rel, f"Local image not found: {value}")
                elif os.path.getsize(local) < 5000:
                    self.add_issue("ERROR", "IMAGE_TOO_SMALL", rel, f"Image file suspiciously small: {value}")

        if image and image != expected:
            self.add_issue("WARN", "IMAGE_PATH_MISMATCH", rel, f"Expected image path {expected}, got {image}")

        if meta.get("image_status") in {"needs_image", "needs_review"}:
            self.add_issue("ERROR", "NEEDS_IMAGE", rel, f"image_status={meta.get('image_status')}")

        if meta.get("image_reject_reason") and image:
            self.add_issue(
                "ERROR",
                "IMAGE_REJECT_REASON_WITH_IMAGE",
                rel,
                f"image_reject_reason present while image is set: {meta.get('image_reject_reason')}",
            )

        if meta.get("image_status") == "verified":
            if not clean_text(meta.get("image_source_url")):
                self.add_issue("ERROR", "VERIFIED_IMAGE_NO_SOURCE", rel, "verified image missing image_source_url")
            score = normalize_gate_score(meta.get("image_total_score"))
            if meta.get("image_query") and not is_self_owned_meta(meta):
                if not is_meaningful_gate_score(score):
                    self.add_issue(
                        "ERROR",
                        "IMAGE_SCORE_MISSING",
                        rel,
                        "gate-verified image missing image_total_score",
                    )
                elif not gate_score_passes(score):
                    self.add_issue(
                        "ERROR",
                        "IMAGE_SCORE_LOW",
                        rel,
                        f"image_total_score below gate threshold: {score}",
                    )
            elif (
                is_meaningful_gate_score(score)
                and not gate_score_passes(score)
                and not is_self_owned_meta(meta)
            ):
                self.add_issue(
                    "ERROR",
                    "IMAGE_SCORE_LOW",
                    rel,
                    f"legacy image_total_score below gate threshold: {score}",
                )

        for field_name in IMAGE_REQUIRED:
            if field_missing(meta, field_name):
                self.add_issue("ERROR", "MISSING_IMAGE_METADATA", rel, f"Missing {field_name}")

        if meta.get("image_commercial_use") is not True:
            self.add_issue("ERROR", "COMMERCIAL_USE", rel, "image_commercial_use must be true")

        owner = normalized(meta.get("image_owner"))
        source = normalized(meta.get("image_source"))
        if owner == "self" and source in {"pexels", "pixabay", "unsplash", "freepik"}:
            self.add_issue("ERROR", "IMAGE_OWNER_MISMATCH", rel, "External source cannot use image_owner=self")
        if owner == "external" and not clean_text(meta.get("image_source_url")):
            self.add_issue("ERROR", "MISSING_SOURCE_URL", rel, "External image missing image_source_url")

        platform = normalized(meta.get("image_source"))
        if platform and platform not in ALLOWED_IMAGE_SOURCES:
            self.add_issue("WARN", "UNKNOWN_IMAGE_SOURCE", rel, f"Unknown image_source: {meta.get('image_source')}")

        source_url = clean_text(meta.get("image_source_url"))
        if source_url and platform in SOURCE_DOMAINS:
            host = urlparse(source_url).netloc.lower()
            if not any(domain in host for domain in SOURCE_DOMAINS[platform]):
                self.add_issue(
                    "ERROR",
                    "IMAGE_SOURCE_DOMAIN_MISMATCH",
                    rel,
                    f"image_source={meta.get('image_source')} but URL host is {host}",
                )

    def _verified_creator(self, slug: str, creator: str) -> bool:
        creator_norm = normalized(creator)
        if not creator_norm or is_blocked_creator(creator):
            return False
        entry = self.manifest_by_slug.get(slug) or self.cache_by_slug.get(slug)
        if not entry:
            return False
        expected = normalized(entry.get("creator"))
        return bool(expected) and creator_norm == expected

    def check_image_creator(self, rel: str, meta: dict, slug: str, fname: str) -> None:
        creator = clean_text(meta.get("image_creator"))
        if not creator:
            return
        creator_norm = normalized(creator)
        if is_blocked_creator(creator):
            self.add_issue(
                "ERROR",
                "FAKE_IMAGE_CREATOR",
                rel,
                f"Blocked creator value: {creator}",
                "Set image_creator to empty unless verified by manifest/cache",
            )
            return

        generated = {
            normalized(meta.get("title")),
            normalized(meta.get("slug")),
            normalized(fname),
            normalized(os.path.splitext(fname)[0]),
        }
        if creator_norm in {v for v in generated if v}:
            self.add_issue("ERROR", "GENERATED_IMAGE_CREATOR", rel, f"Creator appears derived from title/slug/file: {creator}")

        if not self._verified_creator(slug, creator):
            self.add_issue(
                "ERROR",
                "UNVERIFIED_IMAGE_CREATOR",
                rel,
                "image_creator is not verified by images.json or image-source-cache.json",
                "Set image_creator to empty or verify from provider metadata",
            )

    def check_ai_summary(self, rel: str, meta: dict) -> None:
        ai = meta.get("ai_summary")
        if not ai or not ai.get("enabled"):
            return
        items = ai.get("items")
        if not isinstance(items, list):
            self.add_issue("ERROR", "AI_SUMMARY_TYPE", rel, "ai_summary.items must be a list")
            return
        for index, item in enumerate(items):
            if not isinstance(item, str):
                self.add_issue("ERROR", "AI_SUMMARY_NON_STRING", rel, f"ai_summary.items[{index}] is not a string")
                continue
            text = clean_text(item)
            if not text:
                self.add_issue("ERROR", "AI_SUMMARY_EMPTY", rel, f"ai_summary.items[{index}] is empty")
            if "map[" in text:
                self.add_issue("ERROR", "AI_SUMMARY_MAP_LITERAL", rel, f"ai_summary.items[{index}] contains map[")
            if len(text) > 350:
                self.add_issue("WARN", "AI_SUMMARY_TOO_LONG", rel, f"ai_summary.items[{index}] exceeds 350 chars")
            if re.search(r"\b(chắc chắn|đảm bảo|100%)\b", text, re.I) and not NEGATED_CLAIM.search(text):
                self.add_issue("WARN", "AI_SUMMARY_OVERCLAIM", rel, f"ai_summary.items[{index}] may overclaim without source")

    def _paragraphs(self, body: str) -> list[str]:
        chunks = re.split(r"\n\s*\n", body)
        return [chunk.strip() for chunk in chunks if chunk.strip()]

    def _has_nearby_source(self, paragraphs: list[str], index: int, meta: dict, body: str) -> bool:
        window = paragraphs[max(0, index - 1): index + 2]
        text = "\n".join(window)
        if MARKDOWN_LINK.search(text) or re.search(r"https?://", text):
            return True
        if ATTRIBUTION_TAGS.search(text):
            return True
        if meta.get("external_links") or meta.get("attribution", {}).get("source_note"):
            return True
        categories = [normalized(c) for c in (meta.get("categories") or [])]
        series = normalized(meta.get("series"))
        if "cong-nghe" in categories and (
            re.search(r"https?://(?:www\.)?apple\.com/", body)
            or re.search(r"https?://support\.apple\.com/", body)
            or series.startswith("ios-27")
            or series.startswith("macos-27")
            or series.startswith("iphone-15")
            or series.startswith("iphone-16")
        ):
            if ATTRIBUTION_TAGS.search(body) or MARKDOWN_LINK.search(body):
                return True
        return False

    def check_claim_sources(self, rel: str, meta: dict, body: str) -> None:
        paragraphs = self._paragraphs(body)
        flagged = False
        for index, paragraph in enumerate(paragraphs):
            if not CLAIM_CONTEXT.search(paragraph) and not CLAIM_STRONG.search(paragraph):
                continue
            if self._has_nearby_source(paragraphs, index, meta, body):
                continue
            if flagged:
                continue
            flagged = True
            severity = "WARN"
            if LEGAL_SENSITIVE.search(paragraph):
                severity = "ERROR"
            elif CLAIM_STRONG.search(paragraph) and self.strict:
                severity = "ERROR"
            self.add_issue(
                severity,
                "CLAIM_WITHOUT_SOURCE",
                rel,
                "Paragraph with factual/legal claim lacks nearby markdown link or source metadata",
                "Add a markdown link or external_links entry near the claim",
            )

    def check_adsense(self, rel: str, meta: dict, body: str) -> None:
        title = clean_text(meta.get("title"))
        if title and ADSENSE_WARN_TITLE.search(title):
            self.add_issue("WARN", "CLICKBAIT_TITLE", rel, "Title contains sensational/overclaim pattern")
        if ADSENSE_BLOCK.search(body):
            self.add_issue("ERROR", "ADSENSE_RISK_CONTENT", rel, "Body matches high-risk AdSense pattern")
        words = word_count(body)
        thin_error = 600 if self.strict else 500
        if words and words < thin_error:
            severity = "ERROR" if words < (400 if not self.strict else 600) else "WARN"
            if self.strict and words < 600:
                severity = "ERROR"
            self.add_issue(
                severity,
                "THIN_CONTENT",
                rel,
                f"Body has only {words} words (< {thin_error})",
            )
        links = MARKDOWN_LINK.findall(body)
        if len(links) > 25:
            self.add_issue("WARN", "EXCESS_EXTERNAL_LINKS", rel, f"Body has {len(links)} external markdown links")

    def check_tone(self, rel: str, body: str) -> None:
        if TONE_WARN.search(body) and not NEGATED_CLAIM.search(body):
            self.add_issue(
                "WARN",
                "PROMOTIONAL_TONE",
                rel,
                "Body contains promotional/sycophantic phrasing",
                "Prefer balanced wording: phù hợp nếu…, nên cân nhắc nếu…",
            )

    def check_repeated_end_sections(self, rel: str, body: str) -> None:
        lines = body.splitlines()
        if not lines:
            return
        tail_start = max(0, int(len(lines) * 0.55))
        for idx in range(tail_start, len(lines)):
            line = lines[idx].strip().lower()
            if line.startswith("## "):
                heading = line[3:].strip()
                if heading in END_SECTION_HEADINGS:
                    self.add_issue(
                        "ERROR",
                        "MANUAL_END_SECTION",
                        rel,
                        f"Manual end section heading near EOF: {heading}",
                        "Remove manual block; let site macros render related/FAQ/sources",
                    )
                    return
            if line.startswith("### ") and line[4:].strip() in END_SECTION_HEADINGS:
                self.add_issue("ERROR", "MANUAL_END_SECTION", rel, f"Manual end subsection: {line[4:].strip()}")

    def check_seo(self, rel: str, meta: dict, slug: str) -> None:
        if meta.get("noindex") is True:
            self.add_issue("WARN", "POST_NOINDEX", rel, "Post has noindex=true")
        tags = meta.get("tags") or []
        if not tags:
            self.add_issue("ERROR", "MISSING_TAGS", rel, "tags is empty")
        if len(tags) > 12:
            self.add_issue("WARN", "TAG_STUFFING", rel, f"Post has {len(tags)} tags (> 12)")

    def check_duplicates(self) -> None:
        titles: dict[str, list[str]] = {}
        descriptions: dict[str, list[str]] = {}
        body_starts: dict[str, list[str]] = {}
        summaries: dict[str, list[str]] = {}

        for item in self.posts_data:
            rel = item["file"]
            title = item["title"]
            description = item["description"]
            if title:
                titles.setdefault(title, []).append(rel)
            if description:
                descriptions.setdefault(description, []).append(rel)
            body_key = item["body_start"]
            if body_key:
                body_starts.setdefault(body_key, []).append(rel)
            summary_key = json.dumps(item["ai_summary"], ensure_ascii=False, sort_keys=True)
            if summary_key and summary_key != "[]":
                summaries.setdefault(summary_key, []).append(rel)

        for label, mapping, code in (
            ("title", titles, "DUPLICATE_TITLE"),
            ("description", descriptions, "DUPLICATE_DESCRIPTION"),
            ("body opening", body_starts, "DUPLICATE_BODY_OPENING"),
            ("ai_summary", summaries, "DUPLICATE_AI_SUMMARY"),
        ):
            for key, files in mapping.items():
                if len(files) > 1:
                    self.add_issue("ERROR", code, files[0], f"Duplicate {label} with {', '.join(files[1:])}")

        for image, files in self.image_paths.items():
            if len(files) > 1:
                self.add_issue("ERROR", "DUPLICATE_IMAGE_PATH", files[0], f"Shared image path {image}: {', '.join(files[1:])}")

        for source_url, files in self.source_urls.items():
            if len(files) > 1 and source_url not in self.whitelist_urls:
                self.add_issue("WARN", "DUPLICATE_IMAGE_SOURCE_URL", files[0], f"Shared source_url: {', '.join(files[1:])}")

    def scan_public_artifacts(self) -> None:
        ai_pattern = re.compile(r"<ul[^>]*\bai-summary__list\b[^>]*>.*?</ul>", re.DOTALL)
        for dirpath, _, filenames in os.walk(PUBLIC_DIR):
            for fname in filenames:
                if not fname.endswith((".html", ".xml", ".json", ".md")):
                    continue
                path = os.path.join(dirpath, fname)
                with open(path, encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
                rel = os.path.relpath(path, ROOT)
                if "map[" in content:
                    if ai_pattern.search(content) and "map[" in ai_pattern.search(content).group(0):
                        self.add_issue("ERROR", "PUBLIC_MAP_LITERAL", rel, "map[ found inside ai-summary HTML")
                    elif "/posts/" in rel:
                        self.add_issue("WARN", "PUBLIC_MAP_LITERAL", rel, "map[ found in built public output")

    def write_report(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {
            "summary": self.report.summary,
            "issues": [asdict(issue) for issue in self.report.issues],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    def print_console_report(self) -> None:
        summary = self.report.summary
        print("=== Content Compliance Report ===")
        print(f"  Files scanned: {summary['files_scanned']}")
        print(f"  Errors:        {summary['errors']}")
        print(f"  Warnings:      {summary['warnings']}")
        print(f"  Fixed:         {summary['fixed']}")
        if not self.report.issues:
            print("\nPASSED: no compliance issues found.")
            return
        print("\nIssues:")
        for issue in self.report.issues:
            print(f"  [{issue.severity}] {issue.code} — {issue.file}")
            print(f"    {issue.message}")
            if issue.suggestion:
                print(f"    Suggestion: {issue.suggestion}")


def run_self_test() -> int:
    """Minimal internal fixtures for critical guardrails."""
    fixtures = [
        {
            "name": "fake-creator.md",
            "front": {
                "title": "Test post with fake creator",
                "date": "2026-07-01 10:00:00+07:00",
                "description": "A long enough description for compliance testing in Vietnamese.",
                "categories": ["cong-nghe"],
                "tags": ["test"],
                "author": "Minh Hoàng",
                "draft": False,
                "image": "images/posts/fake-creator.webp",
                "thumbnail": "images/posts/fake-creator.webp",
                "image_source": "Pexels",
                "image_source_url": "https://www.pexels.com/photo/test-12345/",
                "image_license": "Pexels License",
                "image_commercial_use": True,
                "image_owner": "external",
                "image_creator": "Park Bogum",
            },
            "body": "Nội dung test.\n",
            "expect_codes": {"FAKE_IMAGE_CREATOR", "IMAGE_FILE_MISSING"},
        },
        {
            "name": "map-summary.md",
            "front": {
                "title": "Test map summary",
                "date": "2026-07-01 10:00:00+07:00",
                "description": "A long enough description for compliance testing in Vietnamese.",
                "categories": ["cong-nghe"],
                "tags": ["test"],
                "author": "Minh Hoàng",
                "draft": False,
                "image": "images/posts/map-summary.webp",
                "thumbnail": "images/posts/map-summary.webp",
                "image_source": "Pexels",
                "image_source_url": "https://www.pexels.com/photo/test-23456/",
                "image_license": "Pexels License",
                "image_commercial_use": True,
                "image_owner": "external",
                "ai_summary": {"enabled": True, "items": ["map[key:value]"]},
            },
            "body": "Nội dung test.\n",
            "expect_codes": {"AI_SUMMARY_MAP_LITERAL", "IMAGE_FILE_MISSING"},
        },
        {
            "name": "manual-faq.md",
            "front": {
                "title": "Test manual FAQ end block",
                "date": "2026-07-01 10:00:00+07:00",
                "description": "A long enough description for compliance testing in Vietnamese.",
                "categories": ["cong-nghe"],
                "tags": ["test"],
                "author": "Minh Hoàng",
                "draft": False,
                "image": "images/posts/manual-faq.webp",
                "thumbnail": "images/posts/manual-faq.webp",
                "image_source": "Pexels",
                "image_source_url": "https://www.pexels.com/photo/test-34567/",
                "image_license": "Pexels License",
                "image_commercial_use": True,
                "image_owner": "external",
            },
            "body": "Paragraph one.\n\nParagraph two with more words to avoid thin-content noise in this fixture.\n\n## FAQ\n\n- Question?\n",
            "expect_codes": {"MANUAL_END_SECTION", "IMAGE_FILE_MISSING"},
        },
    ]

    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        posts_dir = os.path.join(tmp, "content", "posts")
        os.makedirs(posts_dir)
        old_root = ROOT
        try:
            import scripts.compliance as module  # type: ignore
        except Exception:
            module = sys.modules[__name__]
        module.CONTENT_DIRS = [posts_dir]
        module.ROOT = tmp
        module.MANIFEST_PATH = os.path.join(tmp, "data", "images.json")
        module.SOURCE_CACHE_PATH = os.path.join(tmp, "data", "image-source-cache.json")
        module.PUBLIC_DIR = os.path.join(tmp, "public")

        for fixture in fixtures:
            path = os.path.join(posts_dir, fixture["name"])
            post = frontmatter.Post(fixture["body"])
            post.metadata = fixture["front"]
            with open(path, "w", encoding="utf-8") as handle:
                frontmatter.dump(post, handle)

            checker = ComplianceChecker(fix=False, strict=True, scan_public=False)
            checker.run()
            found = {issue.code for issue in checker.report.issues}
            missing = fixture["expect_codes"] - found
            if missing:
                print(f"SELF-TEST FAIL {fixture['name']}: missing {sorted(missing)}")
                failures += 1
            else:
                print(f"SELF-TEST PASS {fixture['name']}")

        module.ROOT = old_root
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Review Chân Thật content compliance checker")
    parser.add_argument("--check", action="store_true", help="Explicit check mode (default)")
    parser.add_argument("--fix", action="store_true", help="Apply safe automatic fixes")
    parser.add_argument("--strict", action="store_true", help="Upgrade warnings to errors")
    parser.add_argument("--report-json", default="", help="Write JSON report to path")
    parser.add_argument("--no-public", action="store_true", help="Skip scanning public/ output")
    parser.add_argument("--self-test", action="store_true", help="Run internal self-test fixtures")
    args = parser.parse_args()

    if args.self_test:
        code = run_self_test()
        sys.exit(2 if code else 0)

    try:
        checker = ComplianceChecker(fix=args.fix, strict=args.strict, scan_public=not args.no_public)
        exit_code = checker.run()
        checker.print_console_report()
        report_path = args.report_json or DEFAULT_REPORT
        checker.write_report(report_path)
        print(f"\nReport written: {report_path}")
        sys.exit(exit_code)
    except Exception as exc:
        print(f"COMPLIANCE INTERNAL FAILURE: {exc}")
        sys.exit(2)


if __name__ == "__main__":
    main()