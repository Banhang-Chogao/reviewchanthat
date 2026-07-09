"""
scripts/select_images.py
Provider-cascade image selection for blog posts.
- Reads audit report for posts needing images
- Collects candidates from Pexels -> Pixabay -> Unsplash -> Freepik
- Runs Image Relevance Gate before accepting any thumbnail
- Never falls back to placeholder/fake images
- Outputs data/image-selection-report.json
"""

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


def main():
    load_dotenv()
    print("=== Image Selection: Provider Cascade ===")
    audit = load_audit()
    manifest = load_manifest()
    source_cache = load_source_cache()
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
    for post in audit.get("posts", []):
        slug = post["slug"]
        if slug in existing_slugs:
            continue
        img_path = post.get("image", "")
        local_file = os.path.join("static", img_path) if img_path and not img_path.startswith("http") else ""
        if local_file and os.path.exists(local_file):
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
        print("All posts already have valid real images.")
    else:
        print(f"\nPosts needing real images: {len(needs_image)}")
        for post in needs_image:
            slug = post["slug"]
            title = post.get("title", slug)
            print(f"\n  [{slug}] {title}")

            body = load_post_body(slug)
            print(f"    Running Image Relevance Gate...")
            gate_result = select_best_image(
                post=post,
                body=body,
                providers=enabled_providers,
                used_urls=used_urls,
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
                    print(
                        f"    => GATE ACCEPTED from {selected_provider}: "
                        f"score={entry.get('image_total_score')} query={entry.get('image_query')}"
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
        sys.exit(1)

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
