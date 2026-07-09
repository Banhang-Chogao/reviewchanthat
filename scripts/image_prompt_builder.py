#!/usr/bin/env python3
"""Build semantic image generation prompts from content analysis.

Converts structured content analysis into natural language prompts optimized for
AI image generation (DALL-E, Stable Diffusion, etc.).

Usage:
  from image_prompt_builder import build_image_prompt

  analysis_json = json.load(open("reports/image-context/post.json"))
  prompt = build_image_prompt(analysis_json)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Prompt templates for different topics
PROMPT_TEMPLATES = {
    "general": {
        "style": "professional photography",
        "lighting": "natural lighting, good exposure",
        "mood": "balanced, clear",
        "details": "well-composed, high quality",
    },
    "autumn_leaves": {
        "style": "nature photography, autumn aesthetic",
        "lighting": "warm golden hour sunlight, soft shadows",
        "mood": "nostalgic, peaceful, contemplative",
        "details": "detailed texture of aged leaves, depth of field",
    },
    "korea_travel": {
        "style": "travel photography, cultural documentary",
        "lighting": "natural daylight, vibrant colors",
        "mood": "inviting, cultural, adventurous",
        "details": "authentic Korean architecture, street scenes",
    },
    "thailand_travel": {
        "style": "tropical travel photography",
        "lighting": "tropical sunlight, blue hour, golden hour",
        "mood": "relaxed, exotic, adventurous",
        "details": "Thai temples, beaches, street markets",
    },
    "apple_product": {
        "style": "product photography, tech minimalism",
        "lighting": "professional studio lighting, clean",
        "mood": "premium, innovative, precise",
        "details": "sleek design, attention to detail, premium finish",
    },
    "apple_dma": {
        "style": "tech policy infographic, editorial illustration",
        "lighting": "clean, high contrast",
        "mood": "authoritative, analytical, clear",
        "details": "regulatory symbols, tech icons, policy themes",
    },
    "finance_banking": {
        "style": "business photography, financial theme",
        "lighting": "professional, corporate lighting",
        "mood": "trustworthy, professional, secure",
        "details": "financial symbols, technology, security themes",
    },
}

# Visual metaphor library
VISUAL_METAPHORS = {
    "journey": {
        "elements": ["winding path", "map", "compass", "milestone", "signpost"],
        "style": "symbolic, metaphorical",
    },
    "growth": {
        "elements": ["sprouting plant", "blooming flower", "tree development"],
        "style": "organic, natural",
    },
    "technology": {
        "elements": ["circuit board", "network nodes", "digital elements", "code"],
        "style": "futuristic, tech-forward",
    },
    "time": {
        "elements": ["clock", "hourglass", "calendar", "seasons", "sky"],
        "style": "symbolic, temporal",
    },
    "connection": {
        "elements": ["bridge", "network", "linked elements", "web"],
        "style": "connecting, unified",
    },
    "challenge": {
        "elements": ["mountain", "cliff", "obstacle", "bridge crossing"],
        "style": "dramatic, inspiring",
    },
    "knowledge": {
        "elements": ["book", "light", "key", "door", "map"],
        "style": "illuminating, educational",
    },
}

# Composition presets
COMPOSITIONS = {
    "landscape": "wide landscape format, clear focal point, natural composition",
    "portrait": "vertical portrait composition, centered subject, professional framing",
    "close_up": "macro photography, detailed close-up, depth of field",
    "overhead": "bird's eye view, top-down perspective, compositional balance",
    "wide_angle": "wide angle view, expansive scene, multiple focal points",
    "minimalist": "minimalist composition, negative space, clean layout",
    "triptych": "three-part composition, balanced sections",
}

# Negative prompts (what to avoid)
NEGATIVE_PROMPTS = {
    "general": "text, watermark, blurry, low quality, compressed",
    "people": "people, faces, portraits, crowds",
    "products": "fake products, knockoff brands, generic placeholders",
    "ui": "fake UI, mock screens, deceptive interfaces",
}


@dataclass
class ImagePrompt:
    """Structured image generation prompt."""
    main_subject: str
    style: str
    lighting: str
    mood: str
    composition: str
    keywords: list[str]
    forbidden_keywords: list[str]
    negative_prompt: str

    def to_full_prompt(self, include_negative: bool = False) -> str:
        """Convert to full natural language prompt."""
        parts = [
            f"Subject: {self.main_subject}",
            f"Style: {self.style}",
            f"Lighting: {self.lighting}",
            f"Mood: {self.mood}",
            f"Composition: {self.composition}",
        ]

        if self.keywords:
            parts.append(f"Include: {', '.join(self.keywords)}")

        prompt = ", ".join(parts)

        if include_negative and self.negative_prompt:
            prompt += f"\n\nNegative prompt: {self.negative_prompt}"

        return prompt

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "main_subject": self.main_subject,
            "style": self.style,
            "lighting": self.lighting,
            "mood": self.mood,
            "composition": self.composition,
            "keywords": self.keywords,
            "forbidden_keywords": self.forbidden_keywords,
            "negative_prompt": self.negative_prompt,
            "full_prompt": self.to_full_prompt(),
        }


def build_image_prompt(
    analysis: dict[str, Any],
    composition_override: str | None = None,
    style_override: str | None = None,
) -> ImagePrompt:
    """Build image prompt from content analysis JSON.

    Args:
        analysis: Content analysis dictionary (from analyze_post_for_image.py)
        composition_override: Override default composition
        style_override: Override default style

    Returns:
        ImagePrompt with semantic details for image generation
    """
    title = analysis.get("title", "")
    topic = analysis.get("primary_topic", "general")
    keywords = analysis.get("keywords", [])
    positive_kw = analysis.get("positive_keywords", [])
    forbidden_kw = analysis.get("forbidden_keywords", [])
    tone = analysis.get("tone", [])
    visual_metaphors = analysis.get("visual_metaphors", [])
    composition_hint = analysis.get("composition_hint", "")

    # Get template for topic
    template = PROMPT_TEMPLATES.get(topic, PROMPT_TEMPLATES["general"])

    # Build main subject from title and topic
    subject_parts = [title[:60]]
    if topic and topic != "general":
        subject_parts.append(f"({topic.replace('_', ' ')})")
    main_subject = " ".join(subject_parts)

    # Style: use override or template
    style = style_override or template.get("style", "professional photography")

    # Lighting from template
    lighting = template.get("lighting", "natural lighting, good exposure")

    # Mood: combine template with detected tone
    mood_parts = [template.get("mood", "balanced")]
    if tone:
        mood_parts.extend(tone)
    mood = ", ".join(set(mood_parts))

    # Composition: use override, hint, or default
    if composition_override:
        composition = composition_override
    elif composition_hint:
        composition = composition_hint
    else:
        composition = COMPOSITIONS.get("landscape", "balanced composition")

    # Combine keywords: title words + positive keywords + visual metaphors
    combined_keywords = []
    if positive_kw:
        combined_keywords.extend(positive_kw[:5])
    if keywords:
        combined_keywords.extend(keywords[:3])
    if visual_metaphors:
        for metaphor in visual_metaphors[:2]:
            if metaphor in VISUAL_METAPHORS:
                combined_keywords.extend(VISUAL_METAPHORS[metaphor]["elements"][:2])

    # Deduplicate and limit
    combined_keywords = list(dict.fromkeys(combined_keywords))[:10]

    # Build negative prompt
    negative_parts = [
        NEGATIVE_PROMPTS["general"],
    ]

    # Add topic-specific negative keywords
    if forbidden_kw:
        negative_parts.append(", ".join(forbidden_kw[:5]))

    # Add compliance-based negatives
    if analysis.get("mentions_people"):
        negative_parts.append(NEGATIVE_PROMPTS["people"])
    if analysis.get("mentions_trademarks"):
        negative_parts.append("trademark, logo, copyright")

    negative_prompt = ", ".join(negative_parts)

    return ImagePrompt(
        main_subject=main_subject,
        style=style,
        lighting=lighting,
        mood=mood,
        composition=composition,
        keywords=combined_keywords,
        forbidden_keywords=forbidden_kw,
        negative_prompt=negative_prompt,
    )


def load_analysis_and_build_prompt(
    analysis_json_path: str | Path,
) -> ImagePrompt:
    """Load analysis JSON and build prompt."""
    with open(analysis_json_path, "r", encoding="utf-8") as f:
        analysis = json.load(f)
    return build_image_prompt(analysis)


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        analysis_path = sys.argv[1]
        prompt = load_analysis_and_build_prompt(analysis_path)
        print("\n" + "="*70)
        print("IMAGE PROMPT")
        print("="*70)
        print(prompt.to_full_prompt(include_negative=True))
        print("="*70)
    else:
        # Demo with sample analysis
        sample = {
            "title": "Busan tháng 10 nên đi đâu?",
            "primary_topic": "autumn_leaves",
            "keywords": ["biển", "busan", "mùa"],
            "positive_keywords": ["lá rụng", "mùa thu", "fall foliage", "warm", "brown"],
            "forbidden_keywords": ["flower", "rose", "bloom"],
            "tone": ["travel"],
            "visual_metaphors": [],
            "composition_hint": "landscape with landmark/scene",
            "mentions_people": False,
            "mentions_trademarks": False,
        }
        prompt = build_image_prompt(sample)
        print("\n" + "="*70)
        print("DEMO: BUSAN AUTUMN TRAVEL")
        print("="*70)
        print(prompt.to_full_prompt(include_negative=True))
        print("="*70)
