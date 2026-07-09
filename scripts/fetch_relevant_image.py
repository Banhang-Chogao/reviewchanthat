"""
Fetch and gate stock image candidates for a single post or batch.
Wraps provider cascade + Image Relevance Gate.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import time
from typing import Any
from urllib.parse import quote

from article_image_context import ArticleImageContext, build_context_from_post
from creator_policy import attribution_text, clean_text, sanitize_candidate
from image_relevance_gate import (
    build_vietnamese_alt,
    rank_candidates,
    save_candidates_debug,
)

from image_providers import (
    FreepikProvider,
    PixabayProvider,
    PexelsProvider,
    UnsplashProvider,
    is_placeholder_image,
    load_dotenv,
    nested_dict,
    validate_candidate,
)


def _provider_color_params(ctx: ArticleImageContext, provider_name: str) -> dict[str, str]:
    if provider_name == "Pexels" and ctx.pexels_color:
        return {"color": ctx.pexels_color}
    if provider_name == "Unsplash" and ctx.unsplash_color:
        return {"color": ctx.unsplash_color}
    if provider_name == "Pixabay" and ctx.pixabay_colors:
        return {"colors": ctx.pixabay_colors}
    return {}


def _search_pexels(provider: PexelsProvider, query: str, ctx: ArticleImageContext) -> list[dict[str, Any]]:
    import requests
    api_key = os.environ.get(provider.env_key, "")
    headers = {"Authorization": api_key}
    params = f"query={quote(query)}&orientation=landscape&size=large&per_page=15"
    color = _provider_color_params(ctx, provider.name).get("color")
    if color:
        params += f"&color={quote(color)}"
    url = f"https://api.pexels.com/v1/search?{params}"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        candidates = []
        for photo in resp.json().get("photos", []):
            src = nested_dict(photo.get("src"))
            alt = clean_text(photo.get("alt")) or clean_text(photo.get("url", "").split("/")[-1].replace("-", " "))
            candidates.append(sanitize_candidate({
                "source_platform": "Pexels",
                "source_url": clean_text(photo.get("url")),
                "direct_url": clean_text(src.get("large2x")) or clean_text(src.get("large")),
                "creator": clean_text(photo.get("photographer")),
                "creator_url": clean_text(photo.get("photographer_url")),
                "license": "Pexels License",
                "commercial_use": True,
                "width": photo.get("width", 0),
                "height": photo.get("height", 0),
                "alt": alt,
                "tags": [],
                "query": query,
            }))
        return candidates
    except Exception:
        return []


def _search_pixabay(provider: PixabayProvider, query: str, ctx: ArticleImageContext) -> list[dict[str, Any]]:
    import requests
    api_key = os.environ.get(provider.env_key, "")
    colors = _provider_color_params(ctx, provider.name).get("colors", "")
    colors_param = f"&colors={quote(colors)}" if colors else ""
    url = (
        f"https://pixabay.com/api/?key={api_key}&q={quote(query)}&lang=en"
        f"&image_type=photo&orientation=horizontal&min_width=1200"
        f"&order=popular&safesearch=true&per_page=15{colors_param}"
    )
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return []
        candidates = []
        for hit in resp.json().get("hits", []):
            tags = [t.strip() for t in str(hit.get("tags", "")).split(",") if t.strip()]
            creator = clean_text(hit.get("user"))
            candidates.append(sanitize_candidate({
                "source_platform": "Pixabay",
                "source_url": clean_text(hit.get("pageURL")),
                "direct_url": clean_text(hit.get("largeImageURL")),
                "creator": creator,
                "creator_url": clean_text(hit.get("pageURL")) if creator else "",
                "license": "Pixabay Content License",
                "commercial_use": True,
                "width": hit.get("imageWidth", 0),
                "height": hit.get("imageHeight", 0),
                "alt": " ".join(tags[:6]),
                "tags": tags,
                "query": query,
            }))
        return candidates
    except Exception:
        return []


def _search_unsplash(provider: UnsplashProvider, query: str, ctx: ArticleImageContext) -> list[dict[str, Any]]:
    import requests
    api_key = os.environ.get(provider.env_key, "")
    headers = {"Authorization": f"Client-ID {api_key}"}
    color = _provider_color_params(ctx, provider.name).get("color")
    color_param = f"&color={quote(color)}" if color else ""
    url = f"https://api.unsplash.com/search/photos?query={quote(query)}&orientation=landscape&per_page=15{color_param}"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        candidates = []
        for photo in resp.json().get("results", []):
            links = nested_dict(photo.get("links"))
            urls = nested_dict(photo.get("urls"))
            user = nested_dict(photo.get("user"))
            user_links = nested_dict(user.get("links"))
            alt = clean_text(photo.get("alt_description")) or clean_text(photo.get("description"))
            candidates.append(sanitize_candidate({
                "source_platform": "Unsplash",
                "source_url": clean_text(links.get("html")),
                "direct_url": clean_text(urls.get("regular")),
                "creator": clean_text(user.get("name")),
                "creator_url": clean_text(user_links.get("html")),
                "license": "Unsplash License",
                "commercial_use": True,
                "width": photo.get("width", 0),
                "height": photo.get("height", 0),
                "alt": alt,
                "tags": [clean_text(t.get("title")) for t in photo.get("tags", []) or [] if clean_text(t.get("title"))],
                "query": query,
            }))
        return candidates
    except Exception:
        return []


PROVIDER_SEARCH = {
    "Pexels": _search_pexels,
    "Pixabay": _search_pixabay,
    "Unsplash": _search_unsplash,
}

MIX_PROVIDERS = ("Pexels", "Pixabay")


def _provider_name(candidate: dict[str, Any]) -> str:
    return clean_text(candidate.get("source_platform", ""))


def choose_accepted_candidate(
    ranked: list[dict[str, Any]],
    provider_balance: dict[str, int] | None = None,
) -> dict[str, Any] | None:
    """Pick a gate-approved image, balancing Pexels/Pixabay with random tie-breaks."""
    accepted = [item for item in ranked if item.get("accepted")]
    if not accepted:
        return None

    mix_accepted = [a for a in accepted if _provider_name(a) in MIX_PROVIDERS]
    pool = mix_accepted or accepted

    if provider_balance:
        counts = {name: provider_balance.get(name, 0) for name in MIX_PROVIDERS}
        min_count = min(counts.values()) if counts else 0
        underused = [name for name, count in counts.items() if count == min_count]
        preferred = random.choice(underused)
        preferred_pool = [a for a in pool if _provider_name(a) == preferred]
        if preferred_pool:
            pool = preferred_pool

    max_score = max(item["gate"]["total_score"] for item in pool)
    top = [item for item in pool if item["gate"]["total_score"] >= max_score - 5]
    return random.choice(top)


def collect_candidates(
    post: dict[str, Any],
    body: str,
    providers: list[Any],
    used_urls: set[str],
    per_provider_limit: int = 15,
    custom_queries: list[str] | None = None,
) -> tuple[ArticleImageContext, list[dict[str, Any]]]:
    ctx = build_context_from_post(post, body)
    pool: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    queries = custom_queries if custom_queries else ctx.all_queries()
    for query in queries:
        provider_order = list(providers)
        random.shuffle(provider_order)
        for provider in provider_order:
            search_fn = PROVIDER_SEARCH.get(provider.name)
            if not search_fn:
                raw = provider.search(query, post)
            else:
                raw = search_fn(provider, query, ctx)
            for candidate in raw:
                if is_placeholder_image(candidate):
                    continue
                ok, _ = validate_candidate(candidate, post, used_urls)
                if not ok:
                    continue
                url = candidate.get("source_url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                candidate["query"] = query
                pool.append(candidate)
                if len([c for c in pool if c.get("source_platform") == provider.name]) >= per_provider_limit:
                    break
        if len(pool) >= 50:
            break
        time.sleep(0.15)
    return ctx, pool


def select_best_image(
    post: dict[str, Any],
    body: str = "",
    providers: list[Any] | None = None,
    used_urls: set[str] | None = None,
    used_hashes: set[str] | None = None,
    download_for_gate: bool = True,
    provider_balance: dict[str, int] | None = None,
    custom_queries: list[str] | None = None,
) -> dict[str, Any] | None:
    load_dotenv()
    if providers is None:
        providers = [PexelsProvider(), PixabayProvider(), UnsplashProvider(), FreepikProvider()]
        providers = [p for p in providers if p.is_enabled()]
    used_urls = used_urls or set()

    ctx, pool = collect_candidates(post, body, providers, used_urls, custom_queries=custom_queries)
    if not pool:
        return None

    ranked = rank_candidates(ctx, pool, used_hashes=used_hashes, download=download_for_gate)
    slug = post.get("slug", "post")
    save_candidates_debug(slug, ranked)

    item = choose_accepted_candidate(ranked, provider_balance=provider_balance)
    if item:
        gate = item.get("gate", {})
        return {
            "candidate": item,
            "context": ctx,
            "image_alt": build_vietnamese_alt(ctx, item),
            "image_query": item.get("query", ""),
            "image_semantic_score": gate.get("semantic_score", 0),
            "image_color_score": gate.get("color_score", 0),
            "image_total_score": gate.get("total_score", 0),
            "watermark_text": attribution_text(
                item.get("source_platform", ""),
                item.get("creator", ""),
                verified=bool(item.get("attribution_verified") and item.get("creator")),
            ),
        }
    return {
        "candidate": None,
        "context": ctx,
        "reject_reason": "No candidate passed semantic/color/object gate",
        "top_candidates": ranked[:5],
    }


def manifest_entry_from_selection(slug: str, title: str, selection: dict[str, Any]) -> dict[str, Any] | None:
    candidate = selection.get("candidate")
    if not candidate:
        return None
    image_id = f"img-{hashlib.md5(slug.encode()).hexdigest()[:8]}"
    source_platform = clean_text(candidate["source_platform"])
    creator = clean_text(candidate.get("creator"))
    verified = bool(candidate.get("attribution_verified")) and bool(creator)
    return {
        "slug": slug,
        "title": title,
        "image_id": image_id,
        "source_platform": source_platform,
        "image_provider": source_platform.lower(),
        "source_url": candidate["source_url"],
        "direct_url": candidate["direct_url"],
        "creator": creator if verified else "",
        "creator_url": clean_text(candidate.get("creator_url")) if verified else "",
        "creator_id": clean_text(candidate.get("creator_id")) if verified else "",
        "photo_id": clean_text(candidate.get("photo_id")),
        "raw_provider": candidate.get("raw_provider"),
        "license": candidate["license"],
        "commercial_use": candidate["commercial_use"],
        "local_source_path": f"static/images/posts-src/{slug}.jpg",
        "output_path": f"static/images/posts/{slug}.webp",
        "watermark_text": selection.get("watermark_text") or attribution_text(
            source_platform, creator, verified=verified
        ),
        "provider_used": source_platform,
        "attribution_verified": verified,
        "attribution_source": candidate.get("attribution_source") or (
            f"{source_platform.lower()}_api" if verified else "not_found"
        ),
        "image_query": selection.get("image_query", ""),
        "image_semantic_score": selection.get("image_semantic_score", 0),
        "image_color_score": selection.get("image_color_score", 0),
        "image_total_score": selection.get("image_total_score", 0),
        "image_alt": selection.get("image_alt", ""),
        "gate_verified": True,
    }