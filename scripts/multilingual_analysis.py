#!/usr/bin/env python3
"""Multi-language content analysis (Vietnamese-first).

Enhances analysis for Vietnamese content with:
- Vietnamese-specific tone detection
- Regional visual metaphors
- Locale-aware keyword extraction
- Vietnamese stop word filtering

Usage:
  python3 scripts/multilingual_analysis.py --post content/posts/post.md --lang vi
  python3 scripts/multilingual_analysis.py --post content/posts/post.md --lang en
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from analyze_post_for_image import analyze_post

# Vietnamese cultural visual metaphors
VI_VISUAL_METAPHORS = {
    "hành trình": ["con đường", "bản đồ", "cột mốc", "gác đèn", "chuyến đi"],
    "phát triển": ["cây mọc", "hoa nở", "cây phát triển", "nụ cây"],
    "công nghệ": ["mạch điện", "bánh răng", "mạng lưới", "nút cộng"],
    "thời gian": ["đồng hồ", "lịch", "mùa", "mặt trời", "mặt trăng"],
    "kết nối": ["cầu", "mạng", "sợi chỉ", "bàn tay"],
    "thách thức": ["núi", "vách đá", "chướng ngại", "cầu vượt"],
    "kiến thức": ["sách", "đèn", "chìa khóa", "cửa"],
}

# Vietnamese tone indicators
VI_TONE_INDICATORS = {
    "du lịch": r"du lịch|chuyến đi|điểm đến|khám phá|trải nghiệm",
    "nôn nao": r"vui|tuyệt vời|tươi tắn|háo hức|phấn khích",
    "tĩnh lặng": r"yên tĩnh|bình yên|xuyên tâm|thiền",
    "phân tích": r"phân tích|nghiên cứu|kết luận|giả thuyết|học thuật",
    "kỹ thuật": r"tính năng|api|thuật toán|giao thức|thư viện",
    "cảm xúc": r"đẹp|tuyệt vời|tệ|tuyệt hảo|ghét",
}

# Vietnamese audience profiles
VI_AUDIENCE_PROFILES = {
    "du_khach": {
        "keywords": ["du lịch", "chuyến đi", "điểm đến", "khám phá"],
        "tone": ["travel", "casual"],
        "description": "Nhà du lịch, người thích khám phá",
    },
    "cong_nghe": {
        "keywords": ["công nghệ", "iphone", "phần mềm", "ứng dụng"],
        "tone": ["technical"],
        "description": "Những người yêu thích công nghệ",
    },
    "tai_chinh": {
        "keywords": ["ngân hàng", "tiền", "đầu tư", "tài chính"],
        "tone": ["formal", "technical"],
        "description": "Những người làm việc trong tài chính",
    },
    "sinh_vien": {
        "keywords": ["học", "trường", "giáo dục", "kỹ năng"],
        "tone": ["casual", "travel"],
        "description": "Sinh viên, người trẻ tuổi",
    },
}

# Vietnamese color associations
VI_COLOR_MEANINGS = {
    "đỏ": ["may mắn", "phúc lộc", "Tết", "lễ hội"],
    "vàng": ["quý báu", "hoàng gia", "sự giàu có", "ấm áp"],
    "xanh lá": ["tự nhiên", "sự sống", "mùa xuân", "bình yên"],
    "xanh dương": ["biển", "trời", "tự do", "khám phá"],
    "nâu": ["mùa thu", "cổ kính", "thiên nhiên", "yên bình"],
}


def enhance_vietnamese_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Enhance analysis with Vietnamese-specific insights."""

    # Add Vietnamese visual metaphors
    if "visual_metaphors" not in analysis:
        analysis["visual_metaphors"] = []

    vi_metaphors = []
    keywords_lower = [kw.lower() for kw in analysis.get("keywords", [])]
    for concept, metaphors in VI_VISUAL_METAPHORS.items():
        for keyword in keywords_lower:
            if any(word in keyword for word in [c for c in concept.split()]):
                vi_metaphors.extend(metaphors)

    analysis["vietnamese_visual_metaphors"] = list(set(vi_metaphors))[:5]

    # Enhance color palette with Vietnamese associations
    palette = analysis.get("palette_suggestion", [])
    enhanced_palette = palette.copy()

    for color_en, vi_meanings in VI_COLOR_MEANINGS.items():
        if any(color_en.lower() in p.lower() for p in palette):
            enhanced_palette.append(f"{color_en} ({','.join(vi_meanings[:2])})")

    analysis["vietnamese_palette"] = enhanced_palette

    # Add Vietnamese audience targeting
    topic = analysis.get("primary_topic", "").lower()
    for profile_key, profile in VI_AUDIENCE_PROFILES.items():
        if any(kw in topic for kw in profile["keywords"]):
            analysis["vietnamese_audience"] = profile["description"]
            break

    # Regional adaptation notes
    analysis["regional_notes"] = {
        "market": "Vietnam",
        "language": "Vietnamese",
        "cultural_notes": [
            "Lunar New Year themes preferred over Western holidays",
            "Buddhist/traditional imagery often resonates better",
            "Regional cities (Hanoi, HCMC, Da Nang) highly searchable",
        ],
        "visual_taboos": [
            "Avoid clocks showing 4:00 (unlucky number)",
            "Avoid all-white designs (funeral associations)",
            "Avoid mixing communist/South Vietnamese symbols",
        ],
    }

    return analysis


def enhance_english_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Enhance analysis with English-specific insights."""

    analysis["language"] = "English"
    analysis["regional_notes"] = {
        "market": "Global/English-speaking",
        "language": "English",
        "cultural_notes": [
            "Western holidays and seasons common",
            "Direct, clear communication preferred",
        ],
    }

    return analysis


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-language content analysis")
    parser.add_argument("--post", required=True, help="Post path")
    parser.add_argument("--lang", default="vi", choices=["vi", "en"], help="Language")

    args = parser.parse_args()

    # Analyze post (Part 1)
    post = analyze_post(args.post)
    if not post:
        return 1

    from dataclasses import asdict
    analysis = asdict(post)

    # Enhance with language-specific insights
    if args.lang == "vi":
        analysis = enhance_vietnamese_analysis(analysis)
        print(f"✓ Enhanced with Vietnamese insights")
    elif args.lang == "en":
        analysis = enhance_english_analysis(analysis)
        print(f"✓ Enhanced with English insights")

    # Print enhanced analysis
    import json
    print("\nEnhanced Analysis:")
    print(json.dumps({k: v for k, v in analysis.items() if k.startswith(f"{args.lang}") or k == "regional_notes"}, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
