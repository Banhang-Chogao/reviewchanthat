"""
scripts/select_images.py
Provider-cascade image selection for blog posts.
- Reads audit report for posts needing images
- Collects candidates from Pexels -> Pixabay -> Unsplash -> Freepik
- Runs Image Relevance Gate before accepting any thumbnail
- Never falls back to placeholder/fake images
- Outputs data/image-selection-report.json
"""

import argparse
import os
import json
import sys
import time

import frontmatter

from creator_policy import clean_text
from fetch_relevant_image import manifest_entry_from_selection, select_best_image
from image_providers import (
    FreepikProvider,
    PexelsProvider,
    PixabayProvider,
    UnsplashProvider,
    is_placeholder_image,
    load_dotenv,
    validate_candidate,
)

AUDIT_REPORT_PATH = "data/image-audit-report.json"
IMAGES_MANIFEST_PATH = "data/images.json"
SELECTION_REPORT_PATH = "data/image-selection-report.json"
SOURCE_CACHE_PATH = "data/image-source-cache.json"
SELF_SOURCE_VALUES = {"self", "self-owned"}


def is_self_owned_post(post: dict) -> bool:
    owner = str(post.get("image_owner", "")).strip().lower()
    source = str(post.get("image_source", "")).strip().lower()
    return owner == "self" or source in SELF_SOURCE_VALUES


def is_self_owned_entry(entry: dict) -> bool:
    platform = str(entry.get("source_platform", "")).strip().lower()
    provider = str(entry.get("provider_used", "")).strip().lower()
    return platform in SELF_SOURCE_VALUES or provider in SELF_SOURCE_VALUES


def load_audit():
    if not os.path.exists(AUDIT_REPORT_PATH):
        print(f"ERROR: Run audit_post_images.py first -- {AUDIT_REPORT_PATH} not found")
        sys.exit(1)
    with open(AUDIT_REPORT_PATH) as f:
        return json.load(f)


def load_manifest():
    if os.path.exists(IMAGES_MANIFEST_PATH):
        with open(IMAGES_MANIFEST_PATH) as f:
            return json.load(f)
    return {"posts": []}


def save_manifest(manifest):
    os.makedirs("data", exist_ok=True)
    with open(IMAGES_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def load_source_cache():
    if os.path.exists(SOURCE_CACHE_PATH):
        with open(SOURCE_CACHE_PATH) as f:
            return json.load(f)
    return {}


def save_source_cache(cache):
    os.makedirs("data", exist_ok=True)
    with open(SOURCE_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def load_post_body(slug: str) -> str:
    content_dir = "content/posts"
    for fname in os.listdir(content_dir):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(content_dir, fname)
        try:
            post = frontmatter.load(fpath)
            if post.metadata.get("slug") == slug:
                return post.content or ""
        except Exception:
            continue
    return ""


def rank_candidates(valid_candidates, post, used_urls):
    """Legacy ranking kept for provider unit compatibility; gate handles final choice."""
    scored = []
    for c in valid_candidates:
        score = 50
        w = c.get("width", 0) or 0
        h = c.get("height", 0) or 0
        if w > 0 and h > 0:
            if w / h >= 1.5:
                score += 15
            if w >= 1920:
                score += 10
        platform = c.get("source_platform", "")
        if platform == "Pexels":
            score += 15
        elif platform == "Unsplash":
            score += 10
        elif platform == "Pixabay":
            score += 5
        if c.get("source_url", "") not in used_urls:
            score += 10
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]


# Apple/iPhone negative brand keywords for filtering
APPLE_NEGATIVE_BRANDS = [
    "oppo", "samsung", "xiaomi", "huawei", "vivo", "realme", "oneplus",
    "android", "galaxy", "xos", "infinix", "tecno", "itel",
]


def _is_apple_post(post):
    """Check if a post is Apple/iPhone topic."""
    title = (str(post.get("title", "")) + " " + str(post.get("slug", ""))).lower()
    apple_kw = ["iphone", "ipad", "ios", "macos", "macbook", "imac", "apple",
                "pro max", "titanium", "dynamic island", "iphone 18"]
    return any(kw in title for kw in apple_kw)


def _filter_brand_candidates(candidates):
    """Filter out candidates whose metadata contains negative brand keywords."""
    filtered = []
    for c in candidates:
        text = json.dumps(c).lower()
        if any(b in text for b in APPLE_NEGATIVE_BRANDS):
            continue
        filtered.append(c)
    return filtered


def _apple_queries(post):
    """Generate Apple-specific search queries for a post."""
    title = (post.get("title") or "").lower()
    slug = post.get("slug") or ""
    if "natural titanium" in title:
        return [
            "iPhone titanium smartphone hand",
            "premium smartphone titanium close up",
            "natural titanium smartphone",
            "silver smartphone camera close up",
            "modern smartphone back camera",
        ]
    if "desert titanium" in title:
        return [
            "gold premium smartphone hand",
            "desert titanium smartphone close up",
            "premium smartphone golden edge",
        ]
    if "titanium" in title:
        return [
            "iPhone titanium smartphone hand",
            "premium smartphone titanium",
            "modern smartphone metal frame",
        ]
    if "iphone" in title:
        return [
            "iPhone premium smartphone hand",
            "modern smartphone camera close up",
            "premium smartphone on table",
            "sleek smartphone technology",
        ]
    return []


def main():
    parser = argparse.ArgumentParser(description="Select stock images with Image Relevance Gate")
    parser.add_argument(
        "--refresh-all",
        action="store_true",
        help="Re-run gate selection for all external posts (keeps self-owned images)",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Exit 0 even if some posts fail the gate (marks needs_review)",
    )
    parser.add_argument(
        "--post",
        type=str,
        help="Single post path to process (e.g. content/posts/iphone-...md)",
    )
    parser.add_argument(
        "--queries",
        type=str,
        help="Comma-separated custom search queries (overrides auto-detection)",
    )
    parser.add_argument(
        "--replace-bad",
        action="store_true",
        help="Force re-selection even if a valid image exists",
    )
    parser.add_argument(
        "--topic",
        type=str,
        help="Topic filter (apple, etc.)",
    )
    args = parser.parse_args()

    load_dotenv()
    title = "Image Selection: Provider Cascade + Gate"
    if args.refresh_all:
        title = "REFRESH ALL: Image Relevance Gate re-selection"
    print(f"=== {title} ===")
    audit = load_audit()
    manifest = load_manifest()
    source_cache = load_source_cache()

    if args.refresh_all:
        manifest["posts"] = [e for e in manifest.get("posts", []) if is_self_owned_entry(e)]
        source_cache = {k: v for k, v in source_cache.items() if is_self_owned_entry(v)}

    existing_slugs = {e["slug"] for e in manifest.get("posts", []) if e.get("direct_url")}
    used_urls = {e.get("source_url", "") for e in manifest.get("posts", []) if e.get("source_url")}

    def upsert_entry(entry):
        for i, e in enumerate(manifest["posts"]):
            if e["slug"] == entry["slug"]:
                manifest["posts"][i] = entry
                return
        manifest["posts"].append(entry)

    providers = [
        PexelsProvider(),
        PixabayProvider(),
        UnsplashProvider(),
        FreepikProvider(),
    ]
    enabled_providers = [p for p in providers if p.is_enabled()]

    if not enabled_providers:
        print("ERROR: No providers have API keys configured.")
        print("Set at least one of: PEXELS_API_KEY, PIXABAY_API_KEY, UNSPLASH_ACCESS_KEY, FREEPIK_API_KEY")
        sys.exit(1)

    print(f"  Enabled providers: {[p.name for p in enabled_providers]}")

    needs_image = []

    # Single post mode
    if args.post:
        post_path = args.post
        if not os.path.exists(post_path):
            print(f"ERROR: Post file not found: {post_path}")
            sys.exit(1)
        try:
            single_post = frontmatter.load(post_path)
            slug = os.path.splitext(os.path.basename(post_path))[0]
            post = {
                "slug": slug,
                "title": single_post.metadata.get("title", ""),
                "image": single_post.metadata.get("image", ""),
                "image_owner": single_post.metadata.get("image_owner", ""),
                "image_source": single_post.metadata.get("image_source", ""),
                "image_status": single_post.metadata.get("image_status", ""),
            }
            if is_self_owned_post(post):
                print(f"Post {slug} is self-owned — skipping")
            else:
                needs_image.append(post)
                existing_slugs.discard(slug)
                used_urls.discard(post.get("image_source_url", ""))
                # Remove existing manifest entry
                manifest["posts"] = [e for e in manifest.get("posts", []) if e.get("slug") != slug]
        except Exception as e:
            print(f"ERROR loading post {post_path}: {e}")
            sys.exit(1)
    else:
        for post in audit.get("posts", []):
            slug = post["slug"]
            if is_self_owned_post(post):
                continue
            if args.refresh_all:
                needs_image.append(post)
                continue
            if not args.replace_bad and slug in existing_slugs:
                continue
            img_path = post.get("image", "")
            local_file = os.path.join("static", img_path) if img_path and not img_path.startswith("http") else ""
            if not args.replace_bad and local_file and os.path.exists(local_file):
                fsize = os.path.getsize(local_file)
                if fsize > 15000:
                    continue
            needs_image.append(post)

    selection_report = {
        "summary": {
            "posts_checked": 0,
            "selected": 0,
            "needs_image": 0,
            "providers_used": {},
        },
        "needs_image": [],
        "selected": [],
    }

    if not needs_image:
        if args.refresh_all:
            print("No external posts to refresh (only self-owned or empty audit).")
        else:
            print("All posts already have valid real images.")
    else:
        print(f"\nPosts needing real images: {len(needs_image)}")
        provider_balance = {"Pexels": 0, "Pixabay": 0}
        for post in needs_image:
            slug = post["slug"]
            title = post.get("title", slug)
            print(f"\n  [{slug}] {title}")

            body = load_post_body(slug)

            # Determine search queries
            custom_queries = None
            if args.queries:
                custom_queries = [q.strip() for q in args.queries.split(",")]
            elif _is_apple_post(post):
                custom_queries = _apple_queries(post)
                if custom_queries:
                    print(f"    Apple-specific queries: {custom_queries}")

            print(f"    Running Image Relevance Gate...")
            gate_result = select_best_image(
                post=post,
                body=body,
                providers=enabled_providers,
                used_urls=used_urls,
                provider_balance=provider_balance,
                custom_queries=custom_queries,
            )
            selected = gate_result.get("candidate") if gate_result else None
            selected_provider = clean_text(selected.get("source_platform")) if selected else None

            if selected:
                entry = manifest_entry_from_selection(slug, title, gate_result)
                if not entry:
                    selected = None
                else:
                    upsert_entry(entry)
                    source_cache[slug] = entry
                    used_urls.add(selected.get("source_url", ""))
                    selection_report["summary"]["selected"] += 1
                    selection_report["selected"].append({
                        "title": title,
                        "slug": slug,
                        "provider": selected_provider,
                        "source_url": selected["source_url"],
                        "image_query": entry.get("image_query", ""),
                        "image_total_score": entry.get("image_total_score", 0),
                    })
                    prov_key = selected_provider
                    selection_report["summary"]["providers_used"][prov_key] = \
                        selection_report["summary"]["providers_used"].get(prov_key, 0) + 1
                    if prov_key in provider_balance:
                        provider_balance[prov_key] += 1
                    print(
                        f"    => GATE ACCEPTED from {selected_provider}: "
                        f"score={entry.get('image_total_score')} query={entry.get('image_query')} "
                        f"mix={provider_balance}"
                    )

            if not selected:
                reject_reason = (gate_result or {}).get("reject_reason", "no_valid_candidate")
                print(f"    FAILED: {reject_reason}")
                selection_report["summary"]["needs_image"] += 1
                selection_report["needs_image"].append({
                    "title": title,
                    "slug": slug,
                    "reason": reject_reason,
                    "top_candidates": (gate_result or {}).get("top_candidates", [])[:5],
                })
                for i, e in enumerate(manifest["posts"]):
                    if e["slug"] == slug:
                        del manifest["posts"][i]
                        break
                source_cache.pop(slug, None)

            selection_report["summary"]["posts_checked"] += 1
            time.sleep(0.3)

    save_manifest(manifest)
    save_source_cache(source_cache)

    os.makedirs("data", exist_ok=True)
    with open(SELECTION_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(selection_report, f, ensure_ascii=False, indent=2)

    print(f"\n=== Selection Report ===")
    print(f"  Posts checked: {selection_report['summary']['posts_checked']}")
    print(f"  Selected: {selection_report['summary']['selected']}")
    print(f"  Needs image: {selection_report['summary']['needs_image']}")
    print(f"  Providers used: {selection_report['summary']['providers_used']}")
    print(f"  Report: {SELECTION_REPORT_PATH}")

    if selection_report["summary"]["needs_image"] > 0:
        print("\n  Posts still needing images:")
        for p in selection_report["needs_image"]:
            print(f"    - {p['title']} ({p['slug']})")
        print("\nWARNING: Posts remain without verified images. Set image_status=needs_review in frontmatter.")
        for p in selection_report["needs_image"]:
            _mark_needs_review(p["slug"], p.get("reason", "No candidate passed semantic/color/object gate"))
        if not args.allow_partial:
            sys.exit(1)
        print("\nPartial refresh completed; some posts marked needs_review.")

    print("\nAll posts have real images selected.")


def _mark_needs_review(slug, reason: str):
    """Clear image fields and mark needs_review when gate finds no acceptable candidate."""
    content_dir = "content/posts"
    for fname in os.listdir(content_dir):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(content_dir, fname)
        try:
            post = frontmatter.load(fpath)
            if post.metadata.get("slug") == slug:
                meta = post.metadata
                for key in [
                    "image", "thumbnail", "image_source", "image_source_url",
                    "image_license", "image_commercial_use", "image_owner",
                    "image_creator", "image_creator_url", "image_provider",
                    "image_query", "image_semantic_score", "image_color_score",
                    "image_total_score", "image_alt",
                ]:
                    meta.pop(key, None)
                meta["image"] = ""
                meta["image_status"] = "needs_review"
                meta["image_reject_reason"] = reason
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(frontmatter.dumps(post))
                print(f"    Cleared image fields, set needs_review: {slug}")
                return
        except Exception:
            continue


if __name__ == "__main__":
    main()
