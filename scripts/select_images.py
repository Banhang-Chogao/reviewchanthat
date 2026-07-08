"""
scripts/select_images.py
Provider-cascade image selection for blog posts.
- Reads audit report for posts needing images
- Generates search keywords from post content
- Tries providers in order: Pexels -> Pixabay -> Unsplash -> Freepik
- Never falls back to placeholder/fake images
- Outputs data/image-selection-report.json
"""

import os
import json
import sys
import hashlib
import time
from urllib.parse import quote

AUDIT_REPORT_PATH = "data/image-audit-report.json"
IMAGES_MANIFEST_PATH = "data/images.json"
SELECTION_REPORT_PATH = "data/image-selection-report.json"
SOURCE_CACHE_PATH = "data/image-source-cache.json"

FALLBACK_KEYWORDS = ["fallback", "placeholder", "generated", "navy", "solid"]
BLOCKED_CREATOR_NAMES = {
    "pexels", "pixabay", "unsplash", "freepik", "park bogum", "park bo-gum",
    "bae suzy", "iu", "yoo jaesuk", "choi wooshik", "lee minho", "lee min ho",
    "kim soo hyun", "song hye kyo",
}
BLOCKED_CREATOR_PHRASES = {
    "unknown photographer", "photographer unknown", "unknown creator",
    "creator unknown", "placeholder",
}


def clean_text(value):
    if isinstance(value, str):
        return value.strip()
    return ""


def normalized(value):
    return " ".join(clean_text(value).casefold().split())


def is_blocked_creator(value):
    value_norm = normalized(value)
    if not value_norm:
        return False
    if value_norm in BLOCKED_CREATOR_NAMES:
        return True
    return any(phrase in value_norm for phrase in BLOCKED_CREATOR_PHRASES)


def sanitize_creator(candidate):
    creator = clean_text(candidate.get("creator"))
    if is_blocked_creator(creator):
        candidate["creator"] = ""
        candidate["creator_url"] = ""
    return candidate


def nested_dict(value):
    if isinstance(value, dict):
        return value
    return {}


def attribution_text(platform, creator, prefix="Source:"):
    platform = clean_text(platform)
    creator = clean_text(creator)
    if not platform:
        return ""
    if creator:
        return f"{prefix} {platform} / {creator}"
    return f"{prefix} {platform}"


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


def load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def generate_keywords(post):
    import re
    title = post.get("title", "")
    tags = post.get("tags", [])
    categories = post.get("categories", [])
    title_clean = re.sub(r"[^\w\s]", " ", title.lower())
    all_words = title_clean.split() + tags + categories
    stopwords = {"và", "của", "cho", "với", "là", "trong", "có", "không", "ở",
                 "khi", "từ", "đến", "những", "đã", "đang", "được", "các", "về",
                 "hay", "nên", "mới", "cũ", "ra", "lại", "qua", "sau", "trước",
                 "the", "a", "an", "and", "or", "for", "of", "in", "to", "is",
                 "it", "on", "that", "this", "with", "be", "at", "by", "from"}
    keywords = [w for w in all_words if w not in stopwords and len(w) > 1]
    return list(dict.fromkeys(keywords))


def build_queries(keywords):
    queries = []
    if len(keywords) >= 3:
        queries.append(" ".join(keywords[:3]))
    if len(keywords) >= 2:
        queries.append(" ".join(keywords[:2]))
    if keywords:
        queries.append(keywords[0])
    if len(keywords) >= 3:
        queries.append(" ".join(keywords[:3]) + " travel")
        queries.append(" ".join(keywords[:2]) + " korea")
    return queries


class BaseProvider:
    name = ""
    env_key = ""

    def is_enabled(self):
        key = os.environ.get(self.env_key, "")
        if not key:
            print(f"    [{self.name}] SKIP: no API key ({self.env_key})")
            return False
        return True

    def search(self, query, post):
        raise NotImplementedError


class PexelsProvider(BaseProvider):
    name = "Pexels"
    env_key = "PEXELS_API_KEY"

    def search(self, query, post):
        import requests
        api_key = os.environ.get(self.env_key, "")
        headers = {"Authorization": api_key}
        url = f"https://api.pexels.com/v1/search?query={quote(query)}&orientation=landscape&per_page=5"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                candidates = []
                for photo in data.get("photos", []):
                    src = nested_dict(photo.get("src"))
                    candidates.append(sanitize_creator({
                        "source_platform": "Pexels",
                        "source_url": clean_text(photo.get("url")),
                        "direct_url": clean_text(src.get("large2x")) or clean_text(src.get("large")),
                        "creator": clean_text(photo.get("photographer")),
                        "creator_url": clean_text(photo.get("photographer_url")),
                        "license": "Pexels License",
                        "commercial_use": True,
                        "width": photo.get("width", 0),
                        "height": photo.get("height", 0),
                    }))
                return candidates
            else:
                print(f"    [{self.name}] API error: {resp.status_code}")
                return []
        except Exception as e:
            print(f"    [{self.name}] request failed: {e}")
            return []


class PixabayProvider(BaseProvider):
    name = "Pixabay"
    env_key = "PIXABAY_API_KEY"

    def search(self, query, post):
        import requests
        api_key = os.environ.get(self.env_key, "")
        category_map = {
            "technology": "technology", "tech": "technology",
            "travel": "travel", "tourism": "travel",
            "nature": "nature", "environment": "nature",
        }
        post_cats = [c.lower() for c in post.get("categories", [])]
        pix_category = "travel"
        for cat in post_cats:
            for k, v in category_map.items():
                if k in cat:
                    pix_category = v
                    break
        url = (f"https://pixabay.com/api/"
               f"?key={api_key}&q={quote(query)}&lang=vi&image_type=photo"
               f"&orientation=horizontal&category={pix_category}"
               f"&min_width=1200&order=popular&safesearch=true&per_page=5")
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                candidates = []
                for hit in data.get("hits", []):
                    creator = clean_text(hit.get("user"))
                    candidates.append(sanitize_creator({
                        "source_platform": "Pixabay",
                        "source_url": clean_text(hit.get("pageURL")),
                        "direct_url": clean_text(hit.get("largeImageURL")),
                        "creator": creator,
                        "creator_url": clean_text(hit.get("pageURL")) if creator else "",
                        "license": "Pixabay Content License",
                        "commercial_use": True,
                        "width": hit.get("imageWidth", 0),
                        "height": hit.get("imageHeight", 0),
                    }))
                return candidates
            else:
                print(f"    [{self.name}] API error: {resp.status_code}")
                return []
        except Exception as e:
            print(f"    [{self.name}] request failed: {e}")
            return []


class UnsplashProvider(BaseProvider):
    name = "Unsplash"
    env_key = "UNSPLASH_ACCESS_KEY"

    def search(self, query, post):
        import requests
        api_key = os.environ.get(self.env_key, "")
        headers = {"Authorization": f"Client-ID {api_key}"}
        url = f"https://api.unsplash.com/search/photos?query={quote(query)}&orientation=landscape&per_page=5"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                candidates = []
                for photo in data.get("results", []):
                    links = nested_dict(photo.get("links"))
                    urls = nested_dict(photo.get("urls"))
                    user = nested_dict(photo.get("user"))
                    user_links = nested_dict(user.get("links"))
                    candidates.append({
                        "source_platform": "Unsplash",
                        "source_url": clean_text(links.get("html")),
                        "direct_url": clean_text(urls.get("regular")),
                        "creator": clean_text(user.get("name")),
                        "creator_url": clean_text(user_links.get("html")),
                        "license": "Unsplash License",
                        "commercial_use": True,
                        "width": photo.get("width", 0),
                        "height": photo.get("height", 0),
                    })
                return candidates
            else:
                print(f"    [{self.name}] API error: {resp.status_code}")
                return []
        except Exception as e:
            print(f"    [{self.name}] request failed: {e}")
            return []


class FreepikProvider(BaseProvider):
    name = "Freepik"
    env_key = "FREEPIK_API_KEY"

    def search(self, query, post):
        import requests
        api_key = os.environ.get(self.env_key, "")
        headers = {"Authorization": api_key}
        url = f"https://api.freepik.com/v1/resources?term={quote(query)}&orientation=landscape&per_page=5"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                candidates = []
                for resource in data.get("data", []):
                    image = nested_dict(resource.get("image"))
                    image_source = nested_dict(image.get("source"))
                    author = nested_dict(resource.get("author"))
                    candidates.append({
                        "source_platform": "Freepik",
                        "source_url": clean_text(resource.get("url")),
                        "direct_url": clean_text(image_source.get("url")),
                        "creator": clean_text(author.get("name")),
                        "creator_url": clean_text(author.get("url")),
                        "license": "Freepik License",
                        "commercial_use": True,
                        "width": resource.get("width", 0),
                        "height": resource.get("height", 0),
                    })
                return candidates
            else:
                print(f"    [{self.name}] API error: {resp.status_code}")
                return []
        except ImportError:
            return []
        except Exception as e:
            print(f"    [{self.name}] request failed: {e}")
            return []


def is_placeholder_image(candidate):
    direct_url = candidate.get("direct_url", "").lower()
    for kw in FALLBACK_KEYWORDS:
        if kw in direct_url:
            return True
    source_url = candidate.get("source_url", "").lower()
    for kw in FALLBACK_KEYWORDS:
        if kw in source_url:
            return True
    w = candidate.get("width", 0) or 0
    h = candidate.get("height", 0) or 0
    if w > 0 and h > 0 and (w < 400 or h < 300):
        return True
    return False


def validate_candidate(candidate, post, used_urls):
    if not candidate.get("source_url"):
        return False, "no_source_url"
    if not candidate.get("direct_url"):
        return False, "no_direct_url"
    if not candidate.get("license"):
        return False, "no_license"
    if not candidate.get("commercial_use"):
        return False, "not_commercial"
    if is_placeholder_image(candidate):
        return False, "placeholder_detected"
    if candidate.get("source_url", "") in used_urls:
        return False, "duplicate_source_url"
    w = candidate.get("width", 0) or 0
    h = candidate.get("height", 0) or 0
    if w > 0 and h > 0:
        if w < 800 or h < 600:
            return False, f"too_small:{w}x{h}"
        if w / h < 1.2:
            return False, f"not_landscape_enough:{w}x{h}"
    return True, "valid"


def rank_candidates(valid_candidates, post, used_urls):
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

            keywords = generate_keywords(post)
            queries = build_queries(keywords)
            print(f"    Keywords: {', '.join(keywords[:8])}")
            print(f"    Queries: {queries[:3]}")

            selected = None
            selected_provider = None
            providers_tried = []
            queries_tried = []

            for query in queries:
                queries_tried.append(query)
                for provider in enabled_providers:
                    if provider.name not in providers_tried:
                        providers_tried.append(provider.name)
                    print(f"    Trying {provider.name} -- query: \"{query}\"")
                    candidates = provider.search(query, post)
                    if not candidates:
                        print(f"      No candidates from {provider.name}")
                        continue
                    valid = []
                    for c in candidates:
                        ok, reason = validate_candidate(c, post, used_urls)
                        if ok:
                            valid.append(c)
                        else:
                            pass
                    if not valid:
                        print(f"      {provider.name}: {len(candidates)} found, 0 valid")
                        continue
                    ranked = rank_candidates(valid, post, used_urls)
                    if ranked:
                        selected = ranked[0]
                        selected_provider = provider.name
                        print(f"      SELECTED from {provider.name}: {selected['source_url']}")
                        break
                if selected:
                    break

            if selected:
                image_id = f"img-{hashlib.md5(slug.encode()).hexdigest()[:8]}"
                source_platform = clean_text(selected["source_platform"])
                creator = clean_text(selected.get("creator"))
                creator_url = clean_text(selected.get("creator_url")) if creator else ""
                entry = {
                    "slug": slug,
                    "title": title,
                    "image_id": image_id,
                    "source_platform": source_platform,
                    "source_url": selected["source_url"],
                    "direct_url": selected["direct_url"],
                    "creator": creator,
                    "creator_url": creator_url,
                    "license": selected["license"],
                    "commercial_use": selected["commercial_use"],
                    "local_source_path": f"static/images/posts-src/{slug}.jpg",
                    "output_path": f"static/images/posts/{slug}.webp",
                    "watermark_text": attribution_text(source_platform, creator),
                    "provider_used": selected_provider,
                }
                upsert_entry(entry)
                source_cache[slug] = entry
                used_urls.add(selected.get("source_url", ""))
                selection_report["summary"]["selected"] += 1
                selection_report["selected"].append({
                    "title": title,
                    "slug": slug,
                    "provider": selected_provider,
                    "source_url": selected["source_url"],
                })
                prov_key = selected_provider
                selection_report["summary"]["providers_used"][prov_key] = \
                    selection_report["summary"]["providers_used"].get(prov_key, 0) + 1
                print(f"    => Registered in manifest from {selected_provider}")
            else:
                print(f"    FAILED: No valid image found from any provider")
                print(f"    Providers tried: {providers_tried}")
                print(f"    Queries tried: {queries_tried}")
                selection_report["summary"]["needs_image"] += 1
                selection_report["needs_image"].append({
                    "title": title,
                    "slug": slug,
                    "queries_tried": queries_tried,
                    "providers_tried": providers_tried,
                    "reason": "no_valid_candidate",
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
        print("\nWARNING: Posts remain without images. Set image_status=needs_image in frontmatter.")
        for p in selection_report["needs_image"]:
            _mark_needs_image(p["slug"])
        sys.exit(1)

    print("\nAll posts have real images selected.")


def _mark_needs_image(slug):
    """Clear all image fields and mark needs_image. No trace of placeholder left."""
    import frontmatter
    content_dir = "content/posts"
    for fname in os.listdir(content_dir):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(content_dir, fname)
        try:
            post = frontmatter.load(fpath)
            if post.metadata.get("slug") == slug:
                meta = post.metadata
                for key in ["image", "thumbnail", "image_source", "image_source_url",
                            "image_license", "image_commercial_use", "image_owner",
                            "image_creator", "image_creator_url"]:
                    meta.pop(key, None)
                meta["image_status"] = "needs_image"
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(frontmatter.dumps(post))
                print(f"    Cleared image fields, set needs_image: {slug}")
                return
        except Exception:
            continue


if __name__ == "__main__":
    main()
