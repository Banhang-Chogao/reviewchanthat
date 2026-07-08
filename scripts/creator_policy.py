"""
Shared image creator attribution policy for Review Chân Thật blog scripts.

Single source of truth for blocked/fake creator names and sanitization helpers.
"""

from __future__ import annotations

import json
import os
from typing import Any

BLOCKED_CREATOR_NAMES = frozenset({
    "pexels", "pixabay", "unsplash", "freepik",
    "park bogum", "park bo-gum", "bae suzy", "iu", "yoo jaesuk", "choi wooshik",
    "lee minho", "lee min ho", "kim soo hyun", "song hye kyo",
    "anonymous", "admin", "review chân thật", "review chan that",
})

BLOCKED_CREATOR_PHRASES = frozenset({
    "unknown photographer", "photographer unknown", "unknown creator",
    "creator unknown", "placeholder",
})


def clean_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def normalized(value: Any) -> str:
    return " ".join(clean_text(value).casefold().split())


def is_blocked_creator(value: Any) -> bool:
    value_norm = normalized(value)
    if not value_norm:
        return False
    if value_norm in BLOCKED_CREATOR_NAMES:
        return True
    return any(phrase in value_norm for phrase in BLOCKED_CREATOR_PHRASES)


def sanitize_creator_pair(creator: Any, creator_url: Any = "") -> tuple[str, str]:
    creator = clean_text(creator)
    creator_url = clean_text(creator_url)
    if is_blocked_creator(creator):
        return "", ""
    if not creator:
        return "", ""
    return creator, creator_url


def attribution_text(platform: Any, creator: Any, prefix: str = "Source:") -> str:
    platform = clean_text(platform)
    creator = clean_text(creator)
    if not platform:
        return ""
    if creator:
        return f"{prefix} {platform} / {creator}"
    return f"{prefix} {platform}"


def sanitize_manifest_entry(entry: dict[str, Any]) -> bool:
    """Normalize creator fields on a manifest/cache entry. Returns True if changed."""
    if not isinstance(entry, dict):
        return False
    before = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    creator, creator_url = sanitize_creator_pair(
        entry.get("creator"),
        entry.get("creator_url"),
    )
    entry["creator"] = creator
    entry["creator_url"] = creator_url
    entry["watermark_text"] = attribution_text(entry.get("source_platform"), creator)
    after = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    return before != after


def sanitize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Sanitize a select_images provider candidate dict in place."""
    creator, creator_url = sanitize_creator_pair(
        candidate.get("creator"),
        candidate.get("creator_url"),
    )
    candidate["creator"] = creator
    candidate["creator_url"] = creator_url
    return candidate


def is_generated_creator(creator: Any, meta: dict[str, Any], fname: str) -> bool:
    creator_norm = normalized(creator)
    if not creator_norm:
        return False
    generated_values = {
        normalized(meta.get("title", "")),
        normalized(meta.get("slug", "")),
        normalized(fname),
        normalized(os.path.splitext(fname)[0]),
        normalized(meta.get("image", "")),
        normalized(os.path.splitext(os.path.basename(clean_text(meta.get("image", ""))))[0]),
    }
    return creator_norm in {v for v in generated_values if v}