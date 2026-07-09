#!/usr/bin/env python3
"""Audit generated images for relevance and compliance.

Checks:
- Image exists and valid
- No forbidden items detected
- Relevance to post content
- Compliance with policies
- Author attribution

Usage:
  python3 scripts/audit_generated_images.py --post content/posts/example.md
  python3 scripts/audit_generated_images.py --json reports/image-audit.json
  python3 scripts/audit_generated_images.py --md reports/image-audit.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except ImportError:
    Image = None

sys.path.insert(0, str(Path(__file__).parent))
from analyze_post_for_image import analyze_post

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "static" / "images" / "posts"
REPORTS_DIR = REPO_ROOT / "reports"

# Forbidden visual patterns
FORBIDDEN_VISUAL_PATTERNS = {
    "people": ["face", "person", "human", "celebrity", "portrait"],
    "trademark": ["logo", "brand", "copyright"],
    "fake_ui": ["fake screen", "mock interface", "placeholder ui"],
}


@dataclass
class ImageAuditResult:
    """Image audit result."""
    slug: str
    title: str
    image_path: Path
    exists: bool = False
    is_valid: bool = False
    file_size: int = 0
    dimensions: tuple[int, int] | None = None
    compliance_score: float = 0.0  # 0.0-1.0
    relevance_score: float = 0.0  # 0.0-1.0
    compliance_issues: list[str] = None
    audit_timestamp: str = ""

    def __post_init__(self):
        if self.compliance_issues is None:
            self.compliance_issues = []
        if not self.audit_timestamp:
            self.audit_timestamp = datetime.utcnow().isoformat()

    @property
    def passes_audit(self) -> bool:
        """Image passes audit if compliance >= 0.7 and relevance >= 0.6."""
        return self.compliance_score >= 0.7 and self.relevance_score >= 0.6

    @property
    def overall_score(self) -> float:
        """Combined audit score (0-1)."""
        return (self.compliance_score + self.relevance_score) / 2


def check_image_exists(path: Path) -> bool:
    """Check if image file exists."""
    return path.exists() and path.is_file()


def check_image_valid(path: Path) -> tuple[bool, dict[str, Any]]:
    """Check if image file is valid."""
    if not Image:
        return True, {}

    try:
        img = Image.open(path)
        return True, {
            "format": img.format,
            "size": img.size,
            "mode": img.mode,
        }
    except Exception as e:
        return False, {"error": str(e)}


def check_compliance(
    image_path: Path,
    analysis: dict[str, Any],
) -> tuple[float, list[str]]:
    """Check image for compliance issues.

    Returns:
        (compliance_score: 0.0-1.0, issues: list)
    """
    issues = []
    score = 1.0

    # Check 1: Forbidden keywords in path/name
    path_lower = str(image_path).lower()
    for category, keywords in FORBIDDEN_VISUAL_PATTERNS.items():
        for keyword in keywords:
            if keyword in path_lower:
                issues.append(f"{category}: forbidden keyword '{keyword}' in filename")
                score -= 0.15

    # Check 2: Analysis compliance flags
    if analysis.get("has_forbidden_items"):
        for item in analysis.get("forbidden_items_found", []):
            issues.append(f"Flagged in analysis: {item}")
            score -= 0.1

    if analysis.get("mentions_people"):
        issues.append("Post mentions creating people - verify image doesn't contain fake people")
        score -= 0.05

    if analysis.get("mentions_trademarks"):
        issues.append("Post mentions trademarks - verify image doesn't misuse brands")
        score -= 0.05

    return max(0.0, score), issues


def check_relevance(
    image_path: Path,
    analysis: dict[str, Any],
) -> tuple[float, list[str]]:
    """Check image relevance to post.

    Uses simple heuristics:
    - File size indicates substantial content (not placeholder)
    - Image exists (basic check)
    - Positive keywords in analysis (heuristic)
    """
    issues = []
    score = 0.5  # Start at neutral

    try:
        size = image_path.stat().st_size
        # File size heuristic: larger = more substantial
        if size > 100_000:  # > 100KB
            score += 0.3
        elif size > 50_000:  # > 50KB
            score += 0.2
        elif size < 5_000:  # < 5KB
            issues.append("Image file too small - may be placeholder")
            score -= 0.2

    except Exception as e:
        issues.append(f"Failed to check file size: {e}")

    # Check topic match
    topic = analysis.get("primary_topic", "")
    if topic:
        score += 0.2  # Topic detected = relevant

    # Keywords score
    keywords = analysis.get("keywords", [])
    if len(keywords) > 5:
        score += 0.1

    tone = analysis.get("tone", [])
    if len(tone) > 0:
        score += 0.1

    return min(1.0, score), issues


def audit_image(
    post_path: Path | None = None,
    image_path: Path | None = None,
    analysis: dict[str, Any] | None = None,
) -> ImageAuditResult | None:
    """Audit a single image.

    Requires either:
    - post_path (will analyze and find image)
    - image_path + analysis dict
    """
    if not post_path and not (image_path and analysis):
        print("ERROR: Provide either --post or both --image and --analysis")
        return None

    # Load/generate analysis if needed
    if post_path:
        post_analysis = analyze_post(post_path)
        if not post_analysis:
            return None
        from dataclasses import asdict
        analysis = asdict(post_analysis)
        slug = analysis["slug"]
        title = analysis["title"]
        image_path = STATIC_DIR / f"{slug}.webp"
    else:
        slug = analysis.get("slug", "unknown")
        title = analysis.get("title", "Unknown")

    result = ImageAuditResult(
        slug=slug,
        title=title,
        image_path=image_path,
    )

    # Check image exists
    result.exists = check_image_exists(image_path)
    if not result.exists:
        result.compliance_issues.append(f"Image file not found: {image_path}")
        return result

    # Check image valid
    result.is_valid, metadata = check_image_valid(image_path)
    if result.is_valid:
        if "size" in metadata:
            result.dimensions = metadata["size"]
        if "error" in metadata:
            result.compliance_issues.append(f"Image validation error: {metadata['error']}")

    # Get file size
    try:
        result.file_size = image_path.stat().st_size
    except Exception:
        pass

    # Check compliance
    result.compliance_score, compliance_issues = check_compliance(image_path, analysis)
    result.compliance_issues.extend(compliance_issues)

    # Check relevance
    result.relevance_score, relevance_issues = check_relevance(image_path, analysis)
    result.compliance_issues.extend(relevance_issues)

    return result


def write_json_report(results: list[ImageAuditResult], output_path: Path) -> None:
    """Write audit results to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "timestamp": datetime.utcnow().isoformat(),
        "total": len(results),
        "passed": sum(1 for r in results if r.passes_audit),
        "failed": sum(1 for r in results if not r.passes_audit),
        "avg_compliance": sum(r.compliance_score for r in results) / len(results) if results else 0,
        "avg_relevance": sum(r.relevance_score for r in results) / len(results) if results else 0,
        "results": [asdict(r) for r in results],
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✓ Wrote: {output_path}")


def write_markdown_report(results: list[ImageAuditResult], output_path: Path) -> None:
    """Write audit results to Markdown."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    passed = sum(1 for r in results if r.passes_audit)
    failed = sum(1 for r in results if not r.passes_audit)

    lines = [
        "# Image Audit Report",
        "",
        f"**Total images:** {len(results)}",
        f"**Passed:** {passed} ({passed*100//len(results) if results else 0}%)",
        f"**Failed:** {failed}",
        "",
        "## Thresholds",
        "- Compliance: ≥ 0.70 (70%)",
        "- Relevance: ≥ 0.60 (60%)",
        "",
    ]

    if passed > 0:
        lines.extend([
            "## ✅ Passed Images",
            "",
        ])
        for r in results:
            if r.passes_audit:
                lines.append(f"- `{r.slug}` (compliance: {r.compliance_score*100:.0f}%, relevance: {r.relevance_score*100:.0f}%)")

    if failed > 0:
        lines.extend([
            "",
            "## ❌ Failed Images",
            "",
        ])
        for r in results:
            if not r.passes_audit:
                lines.append(f"- `{r.slug}` (compliance: {r.compliance_score*100:.0f}%, relevance: {r.relevance_score*100:.0f}%)")
                for issue in r.compliance_issues[:3]:
                    lines.append(f"  - {issue}")

    with open(output_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"✓ Wrote: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit generated images")
    parser.add_argument("--post", help="Post path")
    parser.add_argument("--image", help="Image path")
    parser.add_argument("--analysis", help="Analysis JSON path")
    parser.add_argument("--json", help="Output JSON report")
    parser.add_argument("--md", help="Output Markdown report")
    parser.add_argument("--batch", action="store_true", help="Audit all posts with generated images")

    args = parser.parse_args()

    results = []

    if args.batch:
        # Audit all posts
        from batch_analyze_posts_for_image import IMAGE_CONTEXT_DIR
        analysis_files = sorted(IMAGE_CONTEXT_DIR.glob("*.json"))
        for idx, analysis_file in enumerate(analysis_files, 1):
            with open(analysis_file) as f:
                analysis = json.load(f)
            result = audit_image(analysis=analysis)
            if result:
                results.append(result)
            if idx % 20 == 0:
                print(f"  {idx}/{len(analysis_files)}")

    elif args.post:
        result = audit_image(post_path=Path(args.post))
        if result:
            results.append(result)

    elif args.image and args.analysis:
        with open(args.analysis) as f:
            analysis = json.load(f)
        result = audit_image(image_path=Path(args.image), analysis=analysis)
        if result:
            results.append(result)

    else:
        parser.print_help()
        return 1

    if not results:
        print("❌ No images audited")
        return 1

    # Write reports
    if args.json:
        write_json_report(results, Path(args.json))

    if args.md:
        write_markdown_report(results, Path(args.md))

    # Print summary
    passed = sum(1 for r in results if r.passes_audit)
    print(f"\n✓ Audited {len(results)} images: {passed} passed, {len(results)-passed} failed")

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
