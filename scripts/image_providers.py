"""Shared stock image provider clients and candidate validation."""

from __future__ import annotations

import os
from urllib.parse import quote

from creator_policy import clean_text, sanitize_candidate

FALLBACK_KEYWORDS = ["fallback", "placeholder", "generated", "navy", "solid"]


def nested_dict(value):
    if isinstance(value, dict):
        return value
    return {}


def load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


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
                candidates = []
                for photo in resp.json().get("photos", []):
                    src = nested_dict(photo.get("src"))
                    candidates.append(sanitize_candidate({
                        "source_platform": "Pexels",
                        "source_url": clean_text(photo.get("url")),
                        "direct_url": clean_text(src.get("large2x")) or clean_text(src.get("large")),
                        "creator": clean_text(photo.get("photographer")),
                        "creator_url": clean_text(photo.get("photographer_url")),
                        "creator_id": clean_text(photo.get("photographer_id")),
                        "photo_id": clean_text(photo.get("id")),
                        "license": "Pexels License",
                        "commercial_use": True,
                        "width": photo.get("width", 0),
                        "height": photo.get("height", 0),
                        "alt": clean_text(photo.get("alt")),
                        "raw_provider": {
                            "id": photo.get("id"),
                            "photographer": photo.get("photographer"),
                            "photographer_url": photo.get("photographer_url"),
                            "photographer_id": photo.get("photographer_id"),
                            "url": photo.get("url"),
                        },
                        "attribution_source": "pexels_api",
                    }))
                return candidates
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
        url = (
            f"https://pixabay.com/api/?key={api_key}&q={quote(query)}&lang=en&image_type=photo"
            f"&orientation=horizontal&min_width=1200&order=popular&safesearch=true&per_page=5"
        )
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                candidates = []
                for hit in resp.json().get("hits", []):
                    creator = clean_text(hit.get("user"))
                    tags = [t.strip() for t in str(hit.get("tags", "")).split(",") if t.strip()]
                    user_id = clean_text(hit.get("user_id"))
                    profile = ""
                    if creator and user_id:
                        profile = f"https://pixabay.com/users/{creator.replace(' ', '')}-{user_id}/"
                    candidates.append(sanitize_candidate({
                        "source_platform": "Pixabay",
                        "source_url": clean_text(hit.get("pageURL")),
                        "direct_url": clean_text(hit.get("largeImageURL")),
                        "creator": creator,
                        "creator_url": profile or (clean_text(hit.get("pageURL")) if creator else ""),
                        "creator_id": user_id,
                        "photo_id": clean_text(hit.get("id")),
                        "license": "Pixabay Content License",
                        "commercial_use": True,
                        "width": hit.get("imageWidth", 0),
                        "height": hit.get("imageHeight", 0),
                        "alt": " ".join(tags[:6]),
                        "tags": tags,
                        "raw_provider": {
                            "id": hit.get("id"),
                            "user": hit.get("user"),
                            "user_id": hit.get("user_id"),
                            "pageURL": hit.get("pageURL"),
                        },
                        "attribution_source": "pixabay_api",
                    }))
                return candidates
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
                candidates = []
                for photo in resp.json().get("results", []):
                    links = nested_dict(photo.get("links"))
                    urls = nested_dict(photo.get("urls"))
                    user = nested_dict(photo.get("user"))
                    user_links = nested_dict(user.get("links"))
                    candidates.append(sanitize_candidate({
                        "source_platform": "Unsplash",
                        "source_url": clean_text(links.get("html")),
                        "direct_url": clean_text(urls.get("regular")),
                        "creator": clean_text(user.get("name")),
                        "creator_url": clean_text(user_links.get("html")),
                        "creator_id": clean_text(user.get("id")),
                        "photo_id": clean_text(photo.get("id")),
                        "license": "Unsplash License",
                        "commercial_use": True,
                        "width": photo.get("width", 0),
                        "height": photo.get("height", 0),
                        "alt": clean_text(photo.get("alt_description")) or clean_text(photo.get("description")),
                        "raw_provider": {
                            "id": photo.get("id"),
                            "user": {
                                "name": user.get("name"),
                                "id": user.get("id"),
                                "username": user.get("username"),
                                "links": {"html": user_links.get("html")},
                            },
                            "links": {"html": links.get("html")},
                        },
                        "attribution_source": "unsplash_api",
                    }))
                return candidates
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
                candidates = []
                for resource in resp.json().get("data", []):
                    image = nested_dict(resource.get("image"))
                    image_source = nested_dict(image.get("source"))
                    author = nested_dict(resource.get("author"))
                    candidates.append(sanitize_candidate({
                        "source_platform": "Freepik",
                        "source_url": clean_text(resource.get("url")),
                        "direct_url": clean_text(image_source.get("url")),
                        "creator": clean_text(author.get("name")),
                        "creator_url": clean_text(author.get("url")),
                        "license": "Freepik License",
                        "commercial_use": True,
                        "width": resource.get("width", 0),
                        "height": resource.get("height", 0),
                    }))
                return candidates
            print(f"    [{self.name}] API error: {resp.status_code}")
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