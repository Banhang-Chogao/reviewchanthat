"""
Image Relevance Gate: score and accept/reject stock image candidates for blog posts.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse

import numpy as np
import requests
from PIL import Image

from article_image_context import ArticleImageContext

TOTAL_THRESHOLD = 72
SEMANTIC_THRESHOLD = 28
SEMANTIC_THRESHOLD_PROXY = 14
COLOR_THRESHOLD = 12
CLIP_MAX_CHARS = 240

FLOWER_TERMS = {
    "flower", "flowers", "rose", "roses", "bloom", "blooming", "bouquet",
    "petal", "floral", "garden flower", "fresh flower", "fresh bloom",
    "pink flower", "tropical flower", "spring flower",
}
LEAF_TERMS = {
    "leaf", "leaves", "foliage", "autumn", "fallen", "fall foliage",
    "dry leaves", "forest floor", "maple", "lá rụng", "mùa thu",
}

WARM_HUES = {"brown", "orange", "yellow", "amber", "beige", "warm", "earthy", "gold", "rust"}
COOL_PENALTY_HUES = {"pink", "magenta", "purple", "violet", "cyan", "neon green", "fresh green"}

_CLIP = None


@dataclass
class GateScore:
    semantic_score: float = 0.0
    color_score: float = 0.0
    keyword_metadata_score: float = 0.0
    object_mismatch_penalty: float = 0.0
    quality_score: float = 0.0
    total_score: float = 0.0
    hard_reject: bool = False
    reject_reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def candidate_metadata_text(candidate: dict[str, Any]) -> str:
    parts = [
        candidate.get("alt", ""),
        candidate.get("title", ""),
        candidate.get("description", ""),
        candidate.get("source_url", ""),
        candidate.get("direct_url", ""),
        candidate.get("creator", ""),
        " ".join(candidate.get("tags", []) or []),
    ]
    return _norm(" ".join(str(p) for p in parts if p))


def _topic_is_autumn_leaves(ctx: ArticleImageContext) -> bool:
    blob = _norm(" ".join([ctx.primary_topic, " ".join(ctx.positive_keywords), " ".join(ctx.topic_signals)]))
    return any(term in blob for term in ("autumn", "fall foliage", "fallen leaves", "lá rụng", "mùa thu", "dry leaves"))


def check_hard_reject(ctx: ArticleImageContext, candidate: dict[str, Any]) -> tuple[bool, str]:
    meta = candidate_metadata_text(candidate)
    if not candidate.get("source_url"):
        return True, "missing_source_url"
    if not candidate.get("direct_url"):
        return True, "missing_direct_url"
    if not candidate.get("license"):
        return True, "missing_license"

    for neg in ctx.negative_keywords:
        if _norm(neg) and _norm(neg) in meta:
            return True, f"negative_keyword:{neg}"

    if _topic_is_autumn_leaves(ctx):
        for term in FLOWER_TERMS:
            if term in meta:
                return True, f"autumn_topic_flower_mismatch:{term}"

    if ctx.primary_topic == "korea travel":
        foreign = ("japan", "tokyo", "china beijing", "thailand", "paris", "new york")
        for term in foreign:
            if term in meta and "korea" not in meta and "seoul" not in meta and "busan" not in meta:
                return True, f"korea_topic_foreign_mismatch:{term}"

    if ctx.primary_topic == "finance banking":
        if any(t in meta for t in ("flower", "landscape", "beach", "mountain")) and not any(
            t in meta for t in ("bank", "finance", "payment", "card", "money", "atm")
        ):
            return True, "finance_topic_irrelevant_scene"

    return False, ""


def _keyword_overlap_score(ctx: ArticleImageContext, candidate: dict[str, Any]) -> float:
    meta = candidate_metadata_text(candidate)
    score = 0.0
    hits = 0
    for kw in ctx.positive_keywords:
        token = _norm(kw)
        if token and token in meta:
            hits += 1
            score += 2.5
    penalty = 0.0
    for kw in ctx.negative_keywords:
        token = _norm(kw)
        if token and token in meta:
            penalty += 6.0
    return max(0.0, min(15.0, score - penalty + min(hits, 3)))


def _rgb_to_palette_name(r: int, g: int, b: int) -> str:
    hsv = Image.fromarray(np.uint8([[[r, g, b]]])).convert("HSV").getpixel((0, 0))
    h, s, v = hsv
    if v < 40:
        return "black"
    if s < 25 and v > 200:
        return "white"
    if s < 30:
        if v > 170:
            return "beige"
        return "brown" if v < 120 else "beige"
    hue = h * 2
    if hue < 20 or hue >= 340:
        return "red"
    if hue < 45:
        return "orange"
    if hue < 70:
        return "yellow"
    if hue < 150:
        return "green"
    if hue < 200:
        return "cyan"
    if hue < 260:
        return "blue"
    if hue < 310:
        return "purple"
    return "pink"


def dominant_palette(image: Image.Image, clusters: int = 5) -> list[tuple[str, float]]:
    img = image.convert("RGB").resize((96, 96))
    pixels = np.array(img).reshape(-1, 3).astype(np.float32)
    if len(pixels) < clusters:
        return []
    try:
        from sklearn.cluster import KMeans
        model = KMeans(n_clusters=clusters, n_init=10, random_state=42)
        labels = model.fit_predict(pixels)
        counts = np.bincount(labels, minlength=clusters)
        palette = []
        for idx, center in enumerate(model.cluster_centers_):
            name = _rgb_to_palette_name(int(center[0]), int(center[1]), int(center[2]))
            palette.append((name, counts[idx] / counts.sum()))
        palette.sort(key=lambda x: x[1], reverse=True)
        return palette
    except Exception:
        return []


def color_score(ctx: ArticleImageContext, image: Image.Image) -> tuple[float, dict[str, Any]]:
    if not ctx.desired_palette:
        return 12.0, {"skipped": True, "reason": "no_desired_palette"}

    palette = dominant_palette(image)
    if not palette:
        return 0.0, {"palette": [], "reason": "palette_extract_failed"}

    desired = {_norm(c) for c in ctx.desired_palette}
    warm_targets = desired | WARM_HUES
    score = 0.0
    warm_mass = 0.0
    cool_mass = 0.0
    for name, weight in palette:
        if name in warm_targets or name in {"brown", "orange", "yellow", "amber", "beige", "gold", "rust"}:
            warm_mass += weight
            score += weight * 22
        if name in {"pink", "purple", "cyan", "green"}:
            cool_mass += weight
            score -= weight * 18
        if name == "white" and "earthy" in desired:
            score -= weight * 4

    score = max(0.0, min(25.0, score))
    if warm_mass >= 0.35:
        score = max(score, 14.0)
    if cool_mass >= 0.45 and _topic_is_autumn_leaves(ctx):
        score = min(score, 8.0)
    return score, {"palette": palette, "warm_mass": warm_mass, "cool_mass": cool_mass}


def _clip_model():
    global _CLIP
    if _CLIP is not None:
        return _CLIP
    try:
        from transformers import CLIPModel, CLIPProcessor
        model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        model.eval()
        _CLIP = (model, processor)
        return _CLIP
    except Exception:
        return None


def _clip_text_prompt(ctx: ArticleImageContext, candidate: dict[str, Any]) -> str:
    parts = [
        ctx.primary_topic or ctx.title[:100],
        ", ".join(ctx.positive_keywords[:6]),
        candidate.get("alt") or "",
    ]
    text = ". ".join(p for p in parts if p)
    return text[:CLIP_MAX_CHARS]


def semantic_score(ctx: ArticleImageContext, image: Image.Image, candidate: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    meta = candidate_metadata_text(candidate)
    positive_hits = sum(1 for kw in ctx.positive_keywords if _norm(kw) in meta)
    negative_hits = sum(1 for kw in ctx.negative_keywords if _norm(kw) in meta)
    proxy = max(0.0, min(45.0, 8 + positive_hits * 4 - negative_hits * 10))
    details: dict[str, Any] = {"mode": "keyword_proxy", "positive_hits": positive_hits, "negative_hits": negative_hits}

    if os.environ.get("IMAGE_GATE_CLIP", "1").strip().lower() in {"0", "false", "no"}:
        return proxy, details

    clip_bundle = _clip_model()
    if clip_bundle is None:
        return proxy, details

    try:
        import torch
        model, processor = clip_bundle
        text = _clip_text_prompt(ctx, candidate)
        inputs = processor(
            text=[text],
            images=image,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=77,
        )
        with torch.no_grad():
            outputs = model(**inputs)
            raw = float(outputs.logits_per_image[0][0].item())
        clip_score = max(0.0, min(45.0, (raw - 18.0) * 2.2))
        blended = max(proxy, clip_score * 0.7 + proxy * 0.3)
        details.update({"mode": "clip+proxy", "clip_raw": raw, "proxy": proxy})
        return blended, details
    except Exception as exc:
        details["clip_error"] = str(exc)
        return proxy, details


def object_mismatch_penalty(ctx: ArticleImageContext, candidate: dict[str, Any]) -> tuple[float, str]:
    meta = candidate_metadata_text(candidate)
    penalty = 0.0
    reason = ""
    if _topic_is_autumn_leaves(ctx):
        flower_hits = [t for t in FLOWER_TERMS if t in meta]
        leaf_hits = [t for t in LEAF_TERMS if t in meta]
        if flower_hits and not leaf_hits:
            return 30.0, f"flower_without_leaves:{flower_hits[0]}"
        if flower_hits and leaf_hits:
            penalty += 12.0
            reason = "mixed_flower_and_leaves"
    return penalty, reason


def quality_score(candidate: dict[str, Any], image: Image.Image, used_hashes: set[str] | None = None) -> tuple[float, dict[str, Any]]:
    score = 8.0
    details: dict[str, Any] = {}
    w = int(candidate.get("width", 0) or 0)
    h = int(candidate.get("height", 0) or 0)
    if w >= 1600:
        score += 3
    if w > 0 and h > 0 and w / h >= 1.4:
        score += 2
    if w > 0 and h > 0 and w / h < 1.2:
        score -= 4

    low = candidate_metadata_text(candidate)
    if any(x in low for x in ("watermark", "logo overlay", "text overlay")):
        score -= 8

    try:
        import imagehash
        digest = str(imagehash.phash(image))
        details["phash"] = digest
        if used_hashes and digest in used_hashes:
            score -= 6
    except Exception:
        pass

    return max(0.0, min(15.0, score)), details


def load_image_bytes(data: bytes) -> Image.Image | None:
    try:
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return None


def fetch_image_for_scoring(direct_url: str, timeout: int = 20) -> Image.Image | None:
    if not direct_url:
        return None
    try:
        resp = requests.get(direct_url, timeout=timeout, stream=True)
        if resp.status_code != 200:
            return None
        content = resp.content[:8_000_000]
        return load_image_bytes(content)
    except Exception:
        return None


def score_candidate(
    ctx: ArticleImageContext,
    candidate: dict[str, Any],
    image: Image.Image | None = None,
    used_hashes: set[str] | None = None,
    download: bool = True,
) -> GateScore:
    hard, reason = check_hard_reject(ctx, candidate)
    if hard:
        return GateScore(hard_reject=True, reject_reason=reason, total_score=0.0)

    if image is None and download:
        image = fetch_image_for_scoring(candidate.get("direct_url", ""))
    if image is None:
        return GateScore(hard_reject=True, reject_reason="image_download_failed", total_score=0.0)

    sem, sem_details = semantic_score(ctx, image, candidate)
    col, col_details = color_score(ctx, image)
    kw = _keyword_overlap_score(ctx, candidate)
    mismatch, mismatch_reason = object_mismatch_penalty(ctx, candidate)
    qual, qual_details = quality_score(candidate, image, used_hashes)

    if mismatch >= 30:
        return GateScore(
            semantic_score=sem,
            color_score=col,
            keyword_metadata_score=kw,
            object_mismatch_penalty=mismatch,
            quality_score=qual,
            total_score=0.0,
            hard_reject=True,
            reject_reason=mismatch_reason or "object_mismatch",
            details={"semantic": sem_details, "color": col_details, "quality": qual_details},
        )

    total = sem + col + kw + qual - mismatch
    total = max(0.0, min(100.0, total))
    result = GateScore(
        semantic_score=round(sem, 2),
        color_score=round(col, 2),
        keyword_metadata_score=round(kw, 2),
        object_mismatch_penalty=round(mismatch, 2),
        quality_score=round(qual, 2),
        total_score=round(total, 2),
        details={"semantic": sem_details, "color": col_details, "quality": qual_details, "mismatch_reason": mismatch_reason},
    )
    return result


def accepts(score: GateScore, ctx: ArticleImageContext) -> tuple[bool, str]:
    if score.hard_reject:
        return False, score.reject_reason or "hard_reject"
    semantic_mode = (score.details.get("semantic") or {}).get("mode", "")
    semantic_floor = SEMANTIC_THRESHOLD_PROXY if semantic_mode == "keyword_proxy" else SEMANTIC_THRESHOLD
    if score.semantic_score < semantic_floor:
        return False, f"semantic_below_threshold:{score.semantic_score}"
    if ctx.desired_palette and score.color_score < COLOR_THRESHOLD:
        return False, f"color_below_threshold:{score.color_score}"
    total_floor = 65 if not ctx.desired_palette else TOTAL_THRESHOLD
    if score.total_score < total_floor:
        return False, f"total_below_threshold:{score.total_score}"
    return True, "accepted"


def _metadata_prefilter_score(ctx: ArticleImageContext, candidate: dict[str, Any]) -> float:
    hard, _ = check_hard_reject(ctx, candidate)
    if hard:
        return -1.0
    return _keyword_overlap_score(ctx, candidate)


def rank_candidates(
    ctx: ArticleImageContext,
    candidates: list[dict[str, Any]],
    used_hashes: set[str] | None = None,
    download: bool = True,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    pool = candidates[:limit] if limit else candidates
    if download and len(pool) > 12:
        pool = sorted(pool, key=lambda c: _metadata_prefilter_score(ctx, c), reverse=True)[:12]
    for candidate in pool:
        score = score_candidate(ctx, candidate, used_hashes=used_hashes, download=download)
        ok, reason = accepts(score, ctx)
        item = {
            **candidate,
            "gate": score.to_dict(),
            "accepted": ok,
            "accept_reason": reason,
        }
        ranked.append(item)
    ranked.sort(key=lambda x: (x.get("accepted", False), x["gate"].get("total_score", 0)), reverse=True)
    return ranked


def save_candidates_debug(slug: str, ranked: list[dict[str, Any]]) -> str:
    out_dir = os.path.join("data", "image-candidates")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{slug}.json")
    payload = {
        "slug": slug,
        "candidate_count": len(ranked),
        "candidates": [
            {
                "source_url": c.get("source_url"),
                "provider": c.get("source_platform"),
                "query": c.get("query"),
                "accepted": c.get("accepted"),
                "accept_reason": c.get("accept_reason"),
                "gate": c.get("gate"),
            }
            for c in ranked[:50]
        ],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return path


def build_vietnamese_alt(ctx: ArticleImageContext, candidate: dict[str, Any]) -> str:
    topic = ctx.title or ctx.primary_topic
    provider = candidate.get("source_platform", "stock")
    return f"Ảnh minh họa {topic} — nguồn {provider}"