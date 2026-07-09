#!/usr/bin/env python3
"""Content understanding layer for image generation.

Extract topic, entities, tone, audience, key facts, visual metaphors, and
forbidden items from blog posts to inform smarter, context-aware image generation.

Usage:
  python scripts/analyze_post_for_image.py \\
    --post content/posts/example.md \\
    --out reports/image-context/example.json

  python scripts/analyze_post_for_image.py \\
    --post content/posts/example.md \\
    --out reports/image-context/example.json \\
    --md reports/image-context/example.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import warnings
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml
from sklearn.feature_extraction.text import TfidfVectorizer

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"
REPORTS_DIR = REPO_ROOT / "reports"
IMAGE_CONTEXT_DIR = REPORTS_DIR / "image-context"

# Vietnamese and English stop words
VN_STOP_WORDS = {
    "và", "của", "cho", "với", "là", "trong", "có", "không", "ở", "khi", "từ",
    "đến", "những", "đã", "đang", "được", "các", "về", "hay", "nên", "mới",
    "thì", "này", "như", "có", "năm", "tháng", "ngày", "giờ", "phút", "lúc",
    "nơi", "điểm", "cách", "phía", "dọc", "ngang", "trên", "dưới", "bên",
}

EN_STOP_WORDS = {
    "the", "a", "an", "and", "or", "for", "of", "in", "to", "is", "it", "on",
    "at", "by", "that", "this", "as", "are", "be", "been", "being", "have",
    "has", "had", "do", "does", "did", "will", "would", "should", "could",
    "may", "might", "must", "can", "if", "else", "when", "where", "what",
    "which", "who", "how", "why", "all", "each", "every", "both", "few",
    "more", "most", "other", "some", "such", "no", "nor", "not", "only",
}

# Topic profiles for matched recognition
TOPIC_PROFILES = {
    "apple_dma": {
        # Match DMA regulatory content — requires specific keywords, not just "apple"
        "pattern": r"\b(?:dma|digital.?market|gatekeeper|notarization|steering|sideload|anti-steering)\b",
        "positive_keywords": [
            "dma", "digital markets act", "gatekeeper", "app store", "eu regulation",
            "apple policy", "notarization", "anti-steering", "sideload", "compliance",
        ],
        "forbidden_keywords": [
            "conspiracy", "fake law", "misleading regulation",
        ],
        "tone": "tech, regulatory, analytical",
        "audience": "tech policy enthusiasts, developers, apple users",
    },
    "autumn_leaves": {
        "pattern": r"lá rụng|mùa thu|autumn|fall foliage|fallen leaves|dry leaves|chlorophyll|foliage",
        "positive_keywords": [
            "lá rụng", "mùa thu", "autumn leaves", "fall foliage", "dry leaves",
            "brown", "orange", "warm", "earth tone", "forest", "maple",
        ],
        "forbidden_keywords": [
            "flower", "flowers", "rose", "fresh", "bloom", "bouquet", "garden",
            "pink", "tropical", "spring", "petal", "floral",
        ],
        "tone": "travel, contemplative",
        "audience": "travelers, nature enthusiasts",
    },
    "korea_travel": {
        "pattern": r"korea|hàn quốc|seoul|busan|jeju|hanbok|gyeongbokgung|bukchon",
        "positive_keywords": [
            "korea", "seoul", "busan", "jeju", "hanbok", "korean",
            "temple", "palace", "street", "market", "festival",
        ],
        "forbidden_keywords": [
            "japan", "tokyo", "china", "beijing", "vietnam", "thailand",
        ],
        "tone": "travel, cultural",
        "audience": "travelers, korea enthusiasts",
    },
    "finance_banking": {
        "pattern": r"ngân hàng(?!.*apple)|banking(?!.*apple)|tài chính(?!.*apple)|^(?!.*dma|.*gatekeeper).*(?:thẻ tín dụng|credit card|payment|tiền tệ|tiền gửi)",
        "positive_keywords": [
            "banking", "finance", "credit card", "payment", "atm", "money",
            "transfer", "fintech", "mobile", "transaction", "account",
        ],
        "forbidden_keywords": [
            "random", "nature", "flower", "coffee", "casual",
        ],
        "tone": "informative, technical",
        "audience": "finance users, tech enthusiasts",
    },
    "apple_product": {
        "pattern": r"(?:iphone|ios|macos|macbook|app store|airpods|camera)(?!.*dma|.*gatekeeper)",
        "positive_keywords": [
            "iphone", "ios", "apple", "camera", "design", "technology",
            "feature", "performance", "battery", "screen",
        ],
        "forbidden_keywords": [
            "android", "samsung", "google", "cheapo", "knockoff",
        ],
        "tone": "tech, analytical",
        "audience": "tech enthusiasts, apple users",
    },
    "thailand_travel": {
        "pattern": r"thai.?lan|thailand|bangkok|phuket|chiang.?mai|krabi|koh.?samui",
        "positive_keywords": [
            "thailand", "bangkok", "phuket", "tropical", "beach", "thai",
            "temple", "market", "street", "food", "island",
        ],
        "forbidden_keywords": [
            "japan", "korea", "vietnam only", "europe", "cold",
        ],
        "tone": "travel, relaxed",
        "audience": "travelers, beach enthusiasts",
    },
}

# Entity patterns for common categories
ENTITY_PATTERNS = {
    "location": {
        "vi_pattern": r"(?:ở|tại|du lịch|thành phố|thị trấn|huyện|quận|tỉnh)\s+([A-Z][A-Za-z\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ-]+)",
        "en_pattern": r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:beach|city|island|mountain|town|resort|country)\b",
    },
    "product": {
        "pattern": r"\biPhone|iPad|MacBook|Apple|Samsung|Google|Sony|Canon\b",
    },
    "brand": {
        "pattern": r"\b(?:Starbucks|Nikon|Nike|Adidas|LG|Sony|BMW)\b",
    },
}

# Forbidden keyword patterns that should NOT appear in images
FORBIDDEN_PATTERNS = {
    "autumn_leaves": {
        "patterns": [
            r"flower|rose|bloom|bouquet|petal|floral|daisy|tulip|orchid",
        ],
        "reason": "autumn/fall topic uses tree leaves, not flowers",
    },
    "people_avoidance": {
        "patterns": [
            r"\b(?:celebrity|person|face|human|people|portrait|headshot|mugshot)\b",
        ],
        "reason": "avoid creating fake people/celebrities if not explicitly needed",
    },
    "trademark": {
        "patterns": [
            r"\b(?:McDonald's|Coca-Cola|Pepsi|iPhone\s+product|brand.*product|official.*logo)\b",
        ],
        "reason": "avoid using trademarks/logos without explicit permission",
    },
    "fake_ui": {
        "patterns": [
            r"fake.*(?:screenshot|interface|UI|screen|mockup)",
        ],
        "reason": "avoid creating deceptive fake UI/screenshots",
    },
}

# Tone indicators
TONE_INDICATORS = {
    "formal": r"research|study|analysis|demonstrate|conclusion|hypothesis|academic",
    "casual": r"lol|haha|cool|awesome|hey|guys|friend|love|chill",
    "travel": r"trip|journey|visit|destination|explore|adventure|experience",
    "technical": r"feature|api|code|algorithm|protocol|implement|library|framework",
    "emotional": r"beautiful|amazing|incredible|wonderful|terrible|awful|love|hate",
}

# Visual metaphors - common conceptual mappings
VISUAL_METAPHORS = {
    "journey": ["path", "road", "map", "compass", "signpost", "milestone"],
    "growth": ["plant", "flower", "tree", "sprout", "bud", "bloom"],
    "technology": ["circuit", "gear", "chip", "network", "code", "nodes"],
    "time": ["clock", "hourglass", "calendar", "seasons", "sun", "moon"],
    "connection": ["bridge", "link", "network", "web", "chain", "thread"],
    "challenge": ["mountain", "cliff", "obstacle", "wall", "gap", "bridge"],
    "knowledge": ["book", "lamp", "light", "key", "door", "map"],
    "quality": ["gem", "crystal", "gold", "diamond", "star", "medal"],
}


@dataclass
class ContentAnalysis:
    """Structured output from content analysis."""
    slug: str = ""
    title: str = ""
    description: str = ""

    # Topic and classification
    primary_topic: str = ""
    topic_confidence: float = 0.0
    topic_signals: list[str] = field(default_factory=list)

    # Extracted entities
    entities: dict[str, list[str]] = field(default_factory=dict)  # {category: [values]}
    keywords: list[str] = field(default_factory=list)

    # Tone and audience
    tone: list[str] = field(default_factory=list)  # e.g., ["travel", "casual"]
    tone_scores: dict[str, float] = field(default_factory=dict)
    audience: str = ""
    search_intent: str = ""

    # Visual guidance
    visual_metaphors: list[str] = field(default_factory=list)
    positive_keywords: list[str] = field(default_factory=list)
    forbidden_keywords: list[str] = field(default_factory=list)

    # Content facts
    key_facts: list[str] = field(default_factory=list)
    mentions_people: bool = False
    mentions_products: bool = False
    mentions_trademarks: bool = False

    # Image generation hints
    image_hint: str = ""
    palette_suggestion: list[str] = field(default_factory=list)
    composition_hint: str = ""

    # Compliance flags
    has_forbidden_items: bool = False
    forbidden_items_found: list[str] = field(default_factory=list)


def _normalize_text(text: str) -> str:
    """Normalize text: remove special chars, lowercase, collapse whitespace."""
    text = re.sub(r"[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ-]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _extract_keywords(text: str, max_features: int = 20) -> list[str]:
    """Extract TF-IDF keywords from text."""
    normalized = _normalize_text(text)
    words = normalized.split()

    # Filter stopwords
    stop = VN_STOP_WORDS | EN_STOP_WORDS
    filtered = [w for w in words if w not in stop and len(w) > 2]

    if len(filtered) < 5:
        return filtered[:max_features]

    try:
        vectorizer = TfidfVectorizer(
            max_features=max_features,
            lowercase=True,
            stop_words=None,  # Already filtered
            analyzer="word",
        )
        tfidf_matrix = vectorizer.fit_transform([" ".join(filtered)])
        feature_names = vectorizer.get_feature_names_out()
        return list(feature_names)
    except Exception:
        # Fallback to simple frequency if TF-IDF fails
        from collections import Counter
        return [w for w, _ in Counter(filtered).most_common(max_features)]


def _extract_headings(body: str) -> list[str]:
    """Extract markdown headings."""
    headings = []
    for line in body.splitlines():
        m = re.match(r"^#{1,3}\s+(.+)$", line.strip())
        if m:
            headings.append(m.group(1).strip())
    return headings


def _extract_opening_words(body: str, limit: int = 500) -> str:
    """Extract opening paragraph text for analysis."""
    # Remove code blocks
    text = re.sub(r"```.*?```", " ", body, flags=re.DOTALL)
    # Remove markdown links, keep text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove markdown formatting
    text = re.sub(r"[*_#>`|]", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    words = text.split()
    return " ".join(words[:limit])


def _parse_frontmatter(content: str) -> tuple[dict | None, str]:
    """Parse YAML or TOML frontmatter."""
    if content.startswith("---"):
        m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", content, re.S)
        if m:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    meta = yaml.safe_load(m.group(1)) or {}
                return (meta, m.group(2)) if isinstance(meta, dict) else ({}, m.group(2))
            except Exception:
                return ({}, content)
    if content.startswith("+++"):
        m = re.match(r"^\+\+\+\r?\n(.*?)\r?\n\+\+\+\r?\n?(.*)$", content, re.S)
        if m:
            try:
                meta = tomllib.loads(m.group(1))
                return (meta, m.group(2)) if isinstance(meta, dict) else ({}, m.group(2))
            except Exception:
                return ({}, content)
    return ({}, content)


def _detect_tone(text: str) -> dict[str, float]:
    """Detect tone indicators in text."""
    text_lower = text.lower()
    scores: dict[str, float] = {}

    for tone, pattern in TONE_INDICATORS.items():
        matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
        scores[tone] = min(1.0, matches / max(1, len(text.split()) / 100))

    return scores


def _detect_entities(text: str, body: str = "") -> dict[str, list[str]]:
    """Detect entities in text and body."""
    entities: dict[str, list[str]] = {
        "locations": [],
        "products": [],
        "brands": [],
    }

    corpus = f"{text} {body}".lower()

    # Extract locations (Vietnamese pattern)
    for m in re.finditer(ENTITY_PATTERNS["location"]["vi_pattern"], text, re.IGNORECASE):
        entities["locations"].append(m.group(1))

    # Extract products
    for m in re.finditer(ENTITY_PATTERNS["product"]["pattern"], corpus, re.IGNORECASE):
        entities["products"].append(m.group(0))

    # Extract brands
    for m in re.finditer(ENTITY_PATTERNS["brand"]["pattern"], corpus, re.IGNORECASE):
        entities["brands"].append(m.group(0))

    # Deduplicate
    for key in entities:
        entities[key] = list(set(entities[key]))[:10]

    return entities


def _match_topic_profile(text: str, body: str = "") -> tuple[str, float, dict[str, Any]]:
    """Match text against known topic profiles.

    Orders profiles by specificity: most specific (apple_dma) first,
    then broader location-based (thailand, korea), then general (finance, autumn).
    """
    corpus = f"{text} {body}".lower()

    # Order: most specific first
    profile_order = [
        "apple_dma",  # Most specific regulatory topic
        "thailand_travel",  # Geographic specificity
        "korea_travel",  # Geographic specificity
        "autumn_leaves",  # Seasonal specificity
        "apple_product",  # Product specificity
        "finance_banking",  # Most general
    ]

    best_match = None
    best_profile = {}

    for topic_key in profile_order:
        if topic_key in TOPIC_PROFILES:
            profile = TOPIC_PROFILES[topic_key]
            pattern = profile["pattern"]
            if re.search(pattern, corpus, re.IGNORECASE):
                best_match = topic_key
                best_profile = profile
                break

    confidence = 0.8 if best_match else 0.2
    return best_match or "general", confidence, best_profile


def _detect_forbidden_items(text: str, body: str = "") -> tuple[bool, list[str]]:
    """Detect forbidden items that shouldn't appear in images."""
    corpus = f"{text} {body}".lower()
    found_items = []

    for category, config in FORBIDDEN_PATTERNS.items():
        for pattern in config["patterns"]:
            if re.search(pattern, corpus, re.IGNORECASE):
                found_items.append(f"{category}: {config['reason']}")

    return len(found_items) > 0, found_items


def _extract_key_facts(body: str, headings: list[str]) -> list[str]:
    """Extract key facts from content."""
    facts = []
    lines = body.split("\n")

    # Extract info from lists (marked with - or *)
    for line in lines:
        if re.match(r"^\s*[-*]\s+", line):
            fact = re.sub(r"^\s*[-*]\s+", "", line).strip()
            if fact and len(fact) > 10:
                facts.append(fact[:100])  # Limit to 100 chars

    # Add headings as facts
    for heading in headings:
        if heading and len(heading) > 5:
            facts.append(heading)

    return facts[:15]  # Return top 15


def analyze_post(post_path: str | Path) -> ContentAnalysis | None:
    """Analyze a single blog post for image generation."""
    post_path = Path(post_path)

    if not post_path.exists():
        print(f"ERROR: Post not found: {post_path}", file=sys.stderr)
        return None

    # Read and parse post
    with open(post_path, "r", encoding="utf-8") as f:
        content = f.read()

    meta, body = _parse_frontmatter(content)

    # Extract metadata
    slug = str(meta.get("slug", post_path.stem)).strip()
    title = str(meta.get("title", "")).strip()
    description = str(meta.get("description", "")).strip()

    # Extract content features
    headings = _extract_headings(body)
    opening = _extract_opening_words(body)

    # Build analysis corpus
    analysis_corpus = f"{title} {description} {opening}"
    full_corpus = f"{title} {description} {body}"

    # Detect topic
    primary_topic, topic_conf, topic_profile = _match_topic_profile(title, full_corpus)

    # Extract entities
    entities = _detect_entities(title + " " + description, body)

    # Extract keywords
    keywords = _extract_keywords(analysis_corpus, max_features=15)

    # Detect tone
    tone_scores = _detect_tone(full_corpus)
    tones = [tone for tone, score in tone_scores.items() if score > 0.1]

    # Detect forbidden items
    has_forbidden, forbidden_items = _detect_forbidden_items(title, body)

    # Extract key facts
    key_facts = _extract_key_facts(body, headings)

    # Build analysis object
    analysis = ContentAnalysis(
        slug=slug,
        title=title,
        description=description,
        primary_topic=primary_topic,
        topic_confidence=topic_conf,
        topic_signals=[primary_topic],
        entities=entities,
        keywords=keywords,
        tone=tones,
        tone_scores=tone_scores,
        audience=topic_profile.get("audience", "general audience"),
        search_intent=f"User wants to understand: {primary_topic}",
        visual_metaphors=_extract_visual_metaphors(keywords),
        positive_keywords=topic_profile.get("positive_keywords", keywords[:5]),
        forbidden_keywords=topic_profile.get("forbidden_keywords", []),
        key_facts=key_facts,
        mentions_people="person" in full_corpus or "people" in full_corpus,
        mentions_products=len(entities.get("products", [])) > 0,
        mentions_trademarks=len(entities.get("brands", [])) > 0,
        has_forbidden_items=has_forbidden,
        forbidden_items_found=forbidden_items,
    )

    # Generate image hints
    analysis.image_hint = _generate_image_hint(analysis)
    analysis.palette_suggestion = _suggest_palette(analysis)
    analysis.composition_hint = _suggest_composition(analysis)

    return analysis


def _extract_visual_metaphors(keywords: list[str]) -> list[str]:
    """Extract visual metaphors based on keywords."""
    found_metaphors = []
    keywords_lower = [kw.lower() for kw in keywords]

    for concept, metaphor_list in VISUAL_METAPHORS.items():
        for keyword in keywords_lower:
            if any(word in keyword for word in metaphor_list):
                found_metaphors.append(concept)
                break

    return found_metaphors


def _generate_image_hint(analysis: ContentAnalysis) -> str:
    """Generate a descriptive hint for image generation."""
    parts = []

    if analysis.primary_topic:
        parts.append(f"Topic: {analysis.primary_topic}")

    if analysis.tone:
        parts.append(f"Tone: {', '.join(analysis.tone)}")

    if analysis.positive_keywords:
        parts.append(f"Include: {', '.join(analysis.positive_keywords[:5])}")

    if analysis.forbidden_keywords:
        parts.append(f"Avoid: {', '.join(analysis.forbidden_keywords[:3])}")

    return " | ".join(parts)


def _suggest_palette(analysis: ContentAnalysis) -> list[str]:
    """Suggest color palette based on topic and tone."""
    topic = analysis.primary_topic.lower()

    palette_map = {
        "autumn": ["burnt-orange", "deep-brown", "amber", "warm-gold"],
        "korea": ["traditional-red", "deep-blue", "gold", "white"],
        "beach": ["ocean-blue", "sand-beige", "sky-blue", "turquoise"],
        "tech": ["dark-gray", "neon-blue", "silver", "black"],
        "finance": ["corporate-blue", "dark-green", "gold", "white"],
    }

    for key, palette in palette_map.items():
        if key in topic:
            return palette

    return ["neutral-gray", "warm-neutral", "accent-color"]


def _suggest_composition(analysis: ContentAnalysis) -> str:
    """Suggest composition style for the image."""
    if "travel" in analysis.tone or "destination" in analysis.search_intent.lower():
        return "landscape with landmark/scene, human-scale perspective"

    if "tech" in analysis.tone:
        return "abstract/minimalist tech elements, clean layout"

    if "autumn" in analysis.primary_topic.lower():
        return "close-up nature details, depth-of-field, warm lighting"

    if "product" in analysis.entities:
        return "product-focused, clean background, professional lighting"

    return "balanced composition, clear focal point"


def write_json_report(analysis: ContentAnalysis, output_path: Path) -> None:
    """Write analysis to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = asdict(analysis)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✓ Wrote: {output_path}")


def write_markdown_report(analysis: ContentAnalysis, output_path: Path) -> None:
    """Write human-readable markdown report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Image Context Analysis",
        f"",
        f"**Post:** `{analysis.slug}`",
        f"**Title:** {analysis.title}",
        f"**Description:** {analysis.description}",
        f"",
        f"## Topic & Classification",
        f"",
        f"- **Primary Topic:** {analysis.primary_topic}",
        f"- **Confidence:** {analysis.topic_confidence * 100:.0f}%",
        f"- **Search Intent:** {analysis.search_intent}",
        f"- **Audience:** {analysis.audience}",
        f"",
        f"## Tone & Style",
        f"",
        f"- **Detected Tone:** {', '.join(analysis.tone) or 'neutral'}",
        f"- **Tone Scores:**",
    ]

    for tone, score in sorted(analysis.tone_scores.items(), key=lambda x: x[1], reverse=True):
        if score > 0.05:
            lines.append(f"  - {tone}: {score * 100:.0f}%")

    lines.extend([
        f"",
        f"## Entities",
        f"",
    ])

    for category, values in analysis.entities.items():
        if values:
            lines.append(f"- **{category.title()}:** {', '.join(values)}")

    lines.extend([
        f"",
        f"## Content Analysis",
        f"",
        f"- **Keywords:** {', '.join(analysis.keywords)}",
        f"- **Visual Metaphors:** {', '.join(analysis.visual_metaphors) or 'none'}",
        f"",
        f"## Positive & Forbidden Keywords",
        f"",
        f"- **Include:** {', '.join(analysis.positive_keywords)}",
        f"- **Avoid:** {', '.join(analysis.forbidden_keywords)}",
        f"",
    ])

    if analysis.has_forbidden_items:
        lines.extend([
            f"## ⚠️ Compliance Flags",
            f"",
            f"**Has forbidden items:** YES",
            f"",
        ])
        for item in analysis.forbidden_items_found:
            lines.append(f"- {item}")
        lines.append("")

    lines.extend([
        f"## Image Generation Hints",
        f"",
        f"- **Hint:** {analysis.image_hint}",
        f"- **Palette:** {', '.join(analysis.palette_suggestion)}",
        f"- **Composition:** {analysis.composition_hint}",
        f"",
        f"## Key Facts from Content",
        f"",
    ])

    for fact in analysis.key_facts:
        lines.append(f"- {fact}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"✓ Wrote: {output_path}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze blog post for image generation context"
    )
    parser.add_argument("--post", required=True, help="Path to blog post markdown")
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument("--md", help="Optional markdown report path")

    args = parser.parse_args()

    # Analyze post
    analysis = analyze_post(args.post)
    if not analysis:
        return 1

    # Write outputs
    output_json = Path(args.out)
    write_json_report(analysis, output_json)

    if args.md:
        output_md = Path(args.md)
        write_markdown_report(analysis, output_md)

    # Summary
    print(f"\n✓ Analysis complete:")
    print(f"  Topic: {analysis.primary_topic} ({analysis.topic_confidence*100:.0f}%)")
    print(f"  Tone: {', '.join(analysis.tone) or 'neutral'}")
    print(f"  Audience: {analysis.audience}")
    print(f"  Forbidden items: {'⚠️ YES' if analysis.has_forbidden_items else 'OK'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
