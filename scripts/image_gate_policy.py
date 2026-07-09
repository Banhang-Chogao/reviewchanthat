"""Shared rules for gate-verified vs legacy image metadata."""

from __future__ import annotations

from typing import Any

from image_relevance_gate import TOTAL_THRESHOLD

SELF_SOURCE_VALUES = {"self", "self-owned"}
GATE_MIN_TOTAL_SCORE = 52
GATE_FIELDS = (
    "image_provider",
    "image_query",
    "image_semantic_score",
    "image_color_score",
    "image_total_score",
    "image_alt",
)


def normalized(value: Any) -> str:
    return str(value or "").strip().lower()


def is_self_owned_entry(entry: dict[str, Any]) -> bool:
    platform = normalized(entry.get("source_platform", ""))
    license_val = normalized(entry.get("license", ""))
    return platform in SELF_SOURCE_VALUES or license_val in SELF_SOURCE_VALUES


def is_self_owned_meta(meta: dict[str, Any]) -> bool:
    owner = normalized(meta.get("image_owner"))
    source = normalized(meta.get("image_source"))
    return owner == "self" or source in SELF_SOURCE_VALUES


def is_gate_verified_entry(entry: dict[str, Any]) -> bool:
    return bool(entry.get("gate_verified"))


def resolve_image_status(entry: dict[str, Any]) -> str | None:
    """Return frontmatter image_status, or None to keep legacy (unset) posts."""
    if is_gate_verified_entry(entry):
        return "verified"
    if is_self_owned_entry(entry):
        return "verified"
    return None


def gate_meta_from_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Build gate frontmatter only for gate-verified manifest rows."""
    if not is_gate_verified_entry(entry):
        return None
    meta: dict[str, Any] = {
        "image_provider": normalized(entry.get("source_platform", entry.get("provider_used", ""))),
        "image_query": entry.get("image_query", ""),
        "image_semantic_score": entry.get("image_semantic_score", ""),
        "image_color_score": entry.get("image_color_score", ""),
        "image_total_score": entry.get("image_total_score", ""),
        "image_alt": entry.get("image_alt", ""),
    }
    cleaned = {
        key: value
        for key, value in meta.items()
        if value not in (None, "") and not (key.endswith("_score") and value == 0)
    }
    return cleaned or None


def normalize_gate_score(score: Any) -> Any:
    """Treat zero placeholders as missing gate scores."""
    if score in (None, ""):
        return None
    try:
        return None if float(score) <= 0 else score
    except (TypeError, ValueError):
        return score


def is_meaningful_gate_score(score: Any) -> bool:
    return normalize_gate_score(score) is not None


def requires_gate_score(meta: dict[str, Any]) -> bool:
    """True when post claims gate verification and should carry a real score."""
    if meta.get("image_status") != "verified":
        return False
    if is_self_owned_meta(meta):
        return False
    return bool(meta.get("image_query")) and is_meaningful_gate_score(meta.get("image_total_score"))


def gate_score_passes(score: Any) -> bool:
    try:
        return float(score) >= GATE_MIN_TOTAL_SCORE
    except (TypeError, ValueError):
        return False


def palette_score_passes(score: Any) -> bool:
    try:
        return float(score) >= TOTAL_THRESHOLD
    except (TypeError, ValueError):
        return False