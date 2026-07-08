"""
scripts/select_images.py
AI-assisted image selection for blog posts.
- Reads audit report for posts needing images
- Generates search keywords from post content
- Attempts API search on Pixabay, Pexels, Unsplash (if keys available)
- Falls back to keyword suggestion report for manual sourcing
- Creates/updates data/images.json manifest
"""

import os
import json
import sys
import hashlib
from urllib.parse import quote

AUDIT_REPORT_PATH = "data/image-audit-report.json"
IMAGES_MANIFEST_PATH = "data/images.json"
SOURCE_CACHE_PATH = "data/image-source-cache.json"


def load_audit():
    if not os.path.exists(AUDIT_REPORT_PATH):
        print(f"ERROR: Run audit_post_images.py first — {AUDIT_REPORT_PATH} not found")
        sys.exit(1)
    with open(AUDIT_REPORT_PATH) as f:
        return json.load(f)


def load_manifest():
    if os.path.exists(IMAGES_MANIFEST_PATH):
        with open(IMAGES_MANIFEST_PATH) as f:
            return json.load(f)
    return {"posts": []}


def load_cache():
    if os.path.exists(SOURCE_CACHE_PATH):
        with open(SOURCE_CACHE_PATH) as f:
            return json.load(f)
    return {}


def save_manifest(manifest):
    os.makedirs("data", exist_ok=True)
    with open(IMAGES_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def save_cache(cache):
    os.makedirs("data", exist_ok=True)
    with open(SOURCE_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def generate_keywords(post):
    """Generate image search keywords from post metadata."""
    import re
    title = post.get("title", "")
    tags = post.get("tags", [])
    categories = post.get("categories", [])
    # Clean punctuation, split into words
    title_clean = re.sub(r"[^\w\s]", " ", title.lower())
    all_words = title_clean.split() + tags + categories
    stopwords = {"và", "của", "cho", "với", "là", "trong", "có", "không", "ở",
                 "khi", "từ", "đến", "những", "đã", "đang", "được", "các", "về",
                 "hay", "nên", "mới", "cũ", "ra", "lại", "qua", "sau", "trước",
                 "the", "a", "an", "and", "or", "for", "of", "in", "to", "is",
                 "it", "on", "that", "this", "with", "be", "at", "by", "from"}
    keywords = [w for w in all_words if w not in stopwords and len(w) > 1]
    return list(dict.fromkeys(keywords))  # unique, preserve order


def try_api_search(keywords, platform, post):
    """
    Try to search images via platform API.
    Returns list of candidate dicts or empty list if no API key.
    """
    api_key = os.environ.get(f"{platform.upper()}_API_KEY", "")
    if not api_key:
        return []

    candidates = []
    query = quote(" ".join(keywords[:5]))

    try:
        import requests

        if platform == "pixabay":
            category_map = {
                "technology": "technology", "tech": "technology",
                "ai": "technology", "artificial-intelligence": "technology",
                "programming": "computer", "coding": "computer", "code": "computer", "software": "computer",
                "crypto": "business", "blockchain": "business", "finance": "business", "startup": "business", "marketing": "business",
                "science": "science", "research": "science",
                "nature": "nature", "environment": "nature",
                "education": "education", "learning": "education",
                "health": "health", "medical": "health",
                "travel": "travel", "tourism": "travel",
                "food": "food", "cooking": "food",
                "music": "music",
                "sport": "sports",
                "fashion": "fashion",
                "design": "computer",
                "people": "people",
            }
            post_cats = [c.lower() for c in post.get("categories", [])]
            pix_category = "business"
            for cat in post_cats:
                for k, v in category_map.items():
                    if k in cat:
                        pix_category = v
                        break
            url = (
                f"https://pixabay.com/api/"
                f"?key={api_key}&q={query}&lang=vi&image_type=photo"
                f"&orientation=horizontal&category={pix_category}"
                f"&min_width=1200&order=popular&safesearch=true&per_page=5"
            )
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for hit in data.get("hits", []):
                    candidates.append({
                        "source_platform": "Pixabay",
                        "source_url": hit.get("pageURL", ""),
                        "direct_url": hit.get("largeImageURL", ""),
                        "creator": hit.get("user", ""),
                        "license": "Pixabay Content License",
                        "commercial_use": True,
                        "width": hit.get("imageWidth", 0),
                        "height": hit.get("imageHeight", 0),
                    })
            else:
                print(f"    Pixabay API error: {resp.status_code}")

        elif platform == "pexels":
            headers = {"Authorization": api_key}
            url = f"https://api.pexels.com/v1/search?query={query}&per_page=5"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for photo in data.get("photos", []):
                    candidates.append({
                        "source_platform": "Pexels",
                        "source_url": photo.get("url", ""),
                        "direct_url": photo.get("src", {}).get("large", ""),
                        "creator": photo.get("photographer", ""),
                        "license": "Pexels License",
                        "commercial_use": True,
                        "width": photo.get("width", 0),
                        "height": photo.get("height", 0),
                    })

        elif platform == "unsplash":
            url = f"https://api.unsplash.com/search/photos?query={query}&per_page=5"
            headers = {"Authorization": f"Client-ID {api_key}"}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for result in data.get("results", []):
                    candidates.append({
                        "source_platform": "Unsplash",
                        "source_url": result.get("links", {}).get("html", ""),
                        "direct_url": result.get("urls", {}).get("regular", ""),
                        "creator": result.get("user", {}).get("name", ""),
                        "license": "Unsplash License",
                        "commercial_use": True,
                        "width": result.get("width", 0),
                        "height": result.get("height", 0),
                    })

    except Exception as e:
        print(f"  API search failed for {platform}: {e}")

    return candidates


def score_candidate(candidate, post, used_urls):
    """Score a candidate image from 0-100."""
    score = 50  # base

    # Prefer landscape (width >= height)
    w = candidate.get("width", 0) or 0
    h = candidate.get("height", 0) or 0
    if w > 0 and h > 0:
        if w >= h:
            score += 10
        if w / h >= 1.5:
            score += 10  # wide landscape

    # Penalize reused URLs
    if candidate.get("direct_url", "") in used_urls:
        score -= 30

    # Prefer known platforms
    platform = candidate.get("source_platform", "")
    if platform in ("Pixabay", "Pexels", "Unsplash"):
        score += 10

    return max(0, min(100, score))


def update_frontmatter(slug, image_entry):
    """
    Update the post's frontmatter with new image fields.
    Called later by process_images.py or manually.
    """
    pass  # Implemented in process_images.py


def load_dotenv():
    """Load .env file manually (no external deps)."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def main():
    load_dotenv()
    print("=== AI-Assisted Image Selection ===")
    audit = load_audit()
    manifest = load_manifest()
    cache = load_cache()

    already_done = {e["slug"] for e in manifest.get("posts", []) if e.get("direct_url")}
    existing_slugs = {e["slug"] for e in manifest.get("posts", [])}
    used_urls = {e.get("source_url", "") for e in manifest.get("posts", []) if e.get("source_url")}

    def upsert_entry(entry):
        for i, e in enumerate(manifest["posts"]):
            if e["slug"] == entry["slug"]:
                manifest["posts"][i] = entry
                return
        manifest["posts"].append(entry)

    need_images = []
    for post in audit.get("posts", []):
        slug = post["slug"]
        if slug in already_done:
            continue
        if post["status"] in ("missing_image", "duplicate_image", "missing_license_metadata", "valid"):
            if post.get("image", "").startswith("http") or post["status"] in ("missing_image", "duplicate_image"):
                need_images.append(post)

    if not need_images:
        print("All posts already have images in manifest.")
    else:
        print(f"\nPosts needing images: {len(need_images)}")
        for post in need_images:
            slug = post["slug"]
            title = post["title"]
            print(f"\n  [{slug}] {title}")

            keywords = generate_keywords(post)
            kw_str = ", ".join(keywords[:8])
            print(f"    Keywords: {kw_str}")

            candidates = []
            for platform in ("pixabay", "pexels", "unsplash"):
                results = try_api_search(keywords, platform, post)
                candidates.extend(results)
                if results:
                    print(f"    {platform}: {len(results)} candidates")

            if candidates:
                candidates.sort(key=lambda c: score_candidate(c, post, used_urls), reverse=True)
                best = candidates[0]
                print(f"    Best: {best['source_platform']} | {best['source_url']}")
                image_id = f"img-{hashlib.md5(slug.encode()).hexdigest()[:8]}"
                entry = {
                    "slug": slug,
                    "title": title,
                    "image_id": image_id,
                    "source_platform": best["source_platform"],
                    "source_url": best["source_url"],
                    "direct_url": best["direct_url"],
                    "creator": best.get("creator", ""),
                    "license": best["license"],
                    "commercial_use": best["commercial_use"],
                    "local_source_path": f"static/images/posts-src/{slug}.jpg",
                    "output_path": f"static/images/posts/{slug}.webp",
                    "watermark_text": f"Source: {best['source_platform']}",
                }
                upsert_entry(entry)
                used_urls.add(best.get("direct_url", ""))
                cache[slug] = entry
            else:
                print(f"    No API results — suggest keywords for manual sourcing: {kw_str}")
                entry = {
                    "slug": slug,
                    "title": title,
                    "image_id": f"img-{hashlib.md5(slug.encode()).hexdigest()[:8]}",
                    "source_platform": "",
                    "source_url": "",
                    "direct_url": "",
                    "creator": "",
                    "license": "",
                    "commercial_use": False,
                    "local_source_path": f"static/images/posts-src/{slug}.jpg",
                    "output_path": f"static/images/posts/{slug}.webp",
                    "watermark_text": "",
                    "suggested_keywords": kw_str,
                }
                upsert_entry(entry)
                cache[slug] = {"status": "manual", "keywords": kw_str}

    save_manifest(manifest)
    save_cache(cache)
    print(f"\nManifest saved: {IMAGES_MANIFEST_PATH}")
    print("Posts with images:", len([e for e in manifest["posts"] if e.get("direct_url")]))
    print("Posts needing manual sourcing:", len([e for e in manifest["posts"] if not e.get("direct_url")]))


if __name__ == "__main__":
    main()
