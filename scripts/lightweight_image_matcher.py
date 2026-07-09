"""
Lightweight image matching heuristic for API candidates.

Replaces heavy content compliance scoring with simple rules:
- Check required fields (source_url, direct_url, license, commercial_use)
- Avoid obvious topic mismatches
- Avoid images with logos/watermarks
- Prefer wide/landscape aspect ratios
- Prefer adequate resolution
"""

from __future__ import annotations

import re
from typing import Any

from article_image_context import ArticleImageContext
from creator_policy import clean_text


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def check_required_fields(candidate: dict[str, Any]) -> tuple[bool, str]:
    """Check candidate has all required fields."""
    if not candidate.get("source_url"):
        return False, "missing_source_url"
    if not candidate.get("direct_url"):
        return False, "missing_direct_url"
    if not candidate.get("license"):
        return False, "missing_license"
    if not isinstance(candidate.get("commercial_use"), bool):
        return False, "missing_commercial_use"
    if not candidate.get("commercial_use"):
        return False, "commercial_use_false"
    return True, "ok"


def check_obvious_mismatch(ctx: ArticleImageContext, candidate: dict[str, Any]) -> tuple[bool, str]:
    """Detect obvious topic mismatches without heavy scoring."""
    if not ctx.negative_keywords:
        return True, "no_negative_keywords"

    meta_text = _norm(" ".join([
        candidate.get("alt", ""),
        candidate.get("creator", ""),
        " ".join(candidate.get("tags", []) or []),
    ]))

    # Check for obvious negative keywords
    for neg in ctx.negative_keywords:
        if _norm(neg) and _norm(neg) in meta_text:
            return False, f"negative_keyword:{neg}"

    return True, "ok"


def check_aspect_ratio(candidate: dict[str, Any]) -> tuple[bool, str]:
    """Prefer landscape/wide aspect ratios suitable for hero image (16:9 ≈ 1.78)."""
    w = int(candidate.get("width", 0) or 0)
    h = int(candidate.get("height", 0) or 0)

    if not w or not h:
        return True, "unknown_resolution"

    ratio = w / h
    if ratio < 1.2:
        return False, "too_tall"
    if ratio > 2.5:
        return False, "too_wide"

    return True, "ok"


def check_resolution(candidate: dict[str, Any]) -> tuple[bool, str]:
    """Ensure adequate resolution for hero image (min 1200x630)."""
    w = int(candidate.get("width", 0) or 0)
    h = int(candidate.get("height", 0) or 0)

    if not w or not h:
        return True, "unknown_resolution"

    if w < 1200 or h < 630:
        return False, "too_small"

    return True, "ok"


def check_no_obvious_watermark(candidate: dict[str, Any]) -> tuple[bool, str]:
    """Avoid images with obvious watermarks/logos."""
    text_meta = _norm(" ".join([
        candidate.get("alt", ""),
        candidate.get("description", ""),
    ]))

    watermark_terms = ["watermark", "logo overlay", "text overlay"]
    for term in watermark_terms:
        if term in text_meta:
            return False, f"has_{term}"

    return True, "ok"


def rate_candidate(ctx: ArticleImageContext, candidate: dict[str, Any]) -> dict[str, Any]:
    """
    Rate candidate using lightweight heuristics.
    Returns dict with match_score (0-100) and reasons.
    """
    score = 50  # Start with neutral

    # Check required fields (critical)
    ok, reason = check_required_fields(candidate)
    if not ok:
        return {"match_score": 0, "reasons": [f"required:{reason}"], "accepted": False}

    # Check aspect ratio (important)
    ok, reason = check_aspect_ratio(candidate)
    if ok:
        score += 15
    else:
        score -= 10

    # Check resolution (important)
    ok, reason = check_resolution(candidate)
    if ok:
        score += 15
    else:
        score -= 20

    # Check no obvious watermark (important)
    ok, reason = check_no_obvious_watermark(candidate)
    if ok:
        score += 10
    else:
        score -= 20

    # Check no obvious topic mismatch (very important)
    ok, reason = check_obvious_mismatch(ctx, candidate)
    if not ok:
        score = 0  # Hard reject

    reasons = []
    if score < 0:
        reasons.append("below_minimum")
    if score < 40:
        reasons.append("low_confidence")
    if score >= 70:
        reasons.append("high_confidence")

    accepted = score >= 40
    score = max(0, min(100, score))

    return {
        "match_score": score,
        "reasons": reasons,
        "accepted": accepted,
    }


def choose_best_candidate(
    ctx: ArticleImageContext,
    candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Choose best image from candidates using lightweight matching.
    Returns candidate dict with rating info or None.
    """
    if not candidates:
        return None

    rated = []
    for candidate in candidates:
        rating = rate_candidate(ctx, candidate)
        rated.append({
            **candidate,
            "match_rating": rating,
        })

    # Filter to accepted candidates
    accepted = [c for c in rated if c["match_rating"]["accepted"]]
    if not accepted:
        return None

    # Sort by match_score descending
    accepted.sort(key=lambda c: c["match_rating"]["match_score"], reverse=True)

    return accepted[0]
