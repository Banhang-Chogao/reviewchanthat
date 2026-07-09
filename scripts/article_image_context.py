"""
Extract image-search context from a blog post: topic, keywords, palette, queries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

BROAD_QUERY_BLOCKLIST = {
    "nature", "color", "season", "beautiful", "plant", "beauty", "background",
    "landscape", "outdoor", "scenic", "view", "photo", "image", "wallpaper",
}

TOPIC_PROFILES: list[dict[str, Any]] = [
    {
        "match": (
            r"lá rụng|mùa thu|autumn|fall foliage|fallen leaves|dry leaves|"
            r"chlorophyll|carotenoid|anthocyanin|foliage"
        ),
        "primary_topic": "autumn leaves",
        "positive_keywords": [
            "lá rụng", "mùa thu", "autumn leaves", "fall foliage", "dry leaves",
            "brown orange leaves", "warm earth tone", "forest floor", "fallen leaves",
            "fallen leaf", "maple leaves", "dead leaves",
        ],
        "negative_keywords": [
            "flower", "flowers", "rose", "fresh flower", "bloom", "bouquet",
            "garden flower", "pink flower", "tropical flower", "spring flower",
            "fresh bloom", "petal", "floral",
        ],
        "desired_palette": ["brown", "orange", "yellow", "amber", "beige", "warm", "earthy"],
        "query_candidates_en": [
            "autumn fallen leaves brown orange",
            "dry leaves forest floor",
            "fall foliage warm brown",
            "fallen leaves close up brown",
            "maple leaves autumn ground",
        ],
        "query_candidates_vi": [
            "lá rụng mùa thu nâu cam",
            "lá vàng nâu rơi xuống đất",
            "mùa thu lá khô",
        ],
        "pexels_color": "brown",
        "unsplash_color": "orange",
        "pixabay_colors": "brown,orange,yellow",
    },
    {
        "match": r"korea|hàn quốc|seoul|busan|jeju|hanbok|gyeongbokgung|bukchon",
        "primary_topic": "korea travel",
        "positive_keywords": [
            "korea", "south korea", "seoul", "busan", "jeju", "hanbok",
            "korean street", "korean temple", "korean city",
        ],
        "negative_keywords": [
            "japan tokyo", "china beijing", "vietnam only", "thailand bangkok",
            "europe generic", "random asian street",
        ],
        "desired_palette": [],
        "query_candidates_en": [
            "seoul korea cityscape",
            "busan korea skyline",
            "jeju island korea coast",
            "bukchon hanok village korea",
        ],
        "query_candidates_vi": [
            "du lịch hàn quốc seoul",
            "busan hàn quốc đêm",
            "jeju hàn quốc biển",
        ],
        "pexels_color": "",
        "unsplash_color": "",
        "pixabay_colors": "",
    },
    {
        "match": r"ngân hàng|banking|tài chính|finance|thẻ tín dụng|credit card|payment|ví điện tử",
        "primary_topic": "finance banking",
        "positive_keywords": [
            "banking", "finance", "credit card", "payment", "mobile banking",
            "atm", "money transfer", "fintech",
        ],
        "negative_keywords": [
            "random laptop", "coffee shop", "nature landscape", "flower",
        ],
        "desired_palette": [],
        "query_candidates_en": [
            "mobile banking payment app",
            "credit card finance desk",
            "atm banking transaction",
        ],
        "query_candidates_vi": [
            "ngân hàng thẻ tín dụng",
            "thanh toán di động banking",
        ],
        "pexels_color": "",
        "unsplash_color": "",
        "pixabay_colors": "",
    },
]


@dataclass
class ArticleImageContext:
    slug: str = ""
    title: str = ""
    primary_topic: str = ""
    positive_keywords: list[str] = field(default_factory=list)
    negative_keywords: list[str] = field(default_factory=list)
    desired_palette: list[str] = field(default_factory=list)
    query_candidates_vi: list[str] = field(default_factory=list)
    query_candidates_en: list[str] = field(default_factory=list)
    semantic_prompt: str = ""
    pexels_color: str = ""
    unsplash_color: str = ""
    pixabay_colors: str = ""
    topic_signals: list[str] = field(default_factory=list)

    def all_queries(self) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for q in self.query_candidates_en + self.query_candidates_vi:
            qn = re.sub(r"\s+", " ", q.strip().lower())
            if not qn or qn in seen:
                continue
            if any(blocked == qn or blocked in qn.split() for blocked in BROAD_QUERY_BLOCKLIST if len(qn.split()) <= 2):
                continue
            seen.add(qn)
            ordered.append(q.strip())
        return ordered


def _normalize_words(text: str) -> list[str]:
    text = re.sub(r"[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ-]", " ", text.lower())
    stop = {
        "và", "của", "cho", "với", "là", "trong", "có", "không", "ở", "khi", "từ",
        "đến", "những", "đã", "đang", "được", "các", "về", "hay", "nên", "mới",
        "the", "a", "an", "and", "or", "for", "of", "in", "to", "is", "it", "on",
    }
    return [w for w in text.split() if w not in stop and len(w) > 1]


def _extract_headings(body: str) -> list[str]:
    headings = []
    for line in body.splitlines():
        m = re.match(r"^#{1,3}\s+(.+)$", line.strip())
        if m:
            headings.append(m.group(1).strip())
    return headings


def _opening_words(body: str, limit: int = 800) -> str:
    text = re.sub(r"```.*?```", " ", body, flags=re.DOTALL)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_#>`|]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    words = text.split()
    return " ".join(words[:limit])


def _match_profile(corpus: str) -> dict[str, Any] | None:
    for profile in TOPIC_PROFILES:
        if re.search(profile["match"], corpus, re.I):
            return profile
    return None


def _title_queries(title: str) -> list[str]:
    words = _normalize_words(title)
    queries = []
    if len(words) >= 4:
        queries.append(" ".join(words[:5]))
    if len(words) >= 3:
        queries.append(" ".join(words[:3]))
    return queries


def build_context_from_post(post: dict[str, Any], body: str = "") -> ArticleImageContext:
    title = str(post.get("title", "")).strip()
    slug = str(post.get("slug", "")).strip()
    tags = [str(t) for t in post.get("tags", []) or []]
    categories = [str(c) for c in post.get("categories", []) or []]
    description = str(post.get("description", "")).strip()
    headings = _extract_headings(body)
    opening = _opening_words(body)

    corpus = " ".join([title, description, " ".join(tags), " ".join(categories), " ".join(headings), opening]).lower()
    profile = _match_profile(corpus)

    ctx = ArticleImageContext(slug=slug, title=title)
    if profile:
        ctx.primary_topic = profile["primary_topic"]
        ctx.positive_keywords = list(profile["positive_keywords"])
        ctx.negative_keywords = list(profile["negative_keywords"])
        ctx.desired_palette = list(profile.get("desired_palette", []))
        ctx.query_candidates_en = list(profile.get("query_candidates_en", []))
        ctx.query_candidates_vi = list(profile.get("query_candidates_vi", []))
        ctx.pexels_color = profile.get("pexels_color", "")
        ctx.unsplash_color = profile.get("unsplash_color", "")
        ctx.pixabay_colors = profile.get("pixabay_colors", "")
        ctx.topic_signals = [ctx.primary_topic]
    else:
        words = _normalize_words(" ".join([title, description, " ".join(tags), " ".join(categories)]))
        ctx.primary_topic = " ".join(words[:3]) if words else title
        ctx.positive_keywords = words[:12]
        ctx.query_candidates_en = _title_queries(title)
        ctx.query_candidates_vi = []

    for extra in _title_queries(title):
        if extra not in ctx.query_candidates_en:
            ctx.query_candidates_en.append(extra)

    ctx.semantic_prompt = ". ".join(
        part for part in [
            title,
            ctx.primary_topic,
            ", ".join(ctx.positive_keywords[:10]),
            description[:200] if description else "",
        ] if part
    )
    return ctx