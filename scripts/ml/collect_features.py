#!/usr/bin/env python3
"""
Deploy Failure Feature Collector
=================================
Extracts structured features from blog posts and runs the deploy-failure-healer
to produce labeled training data for the ML pre-deploy risk model.

Usage:
  python3 scripts/ml/collect_features.py --all          # All posts -> JSONL
  python3 scripts/ml/collect_features.py --post <path>  # Single post -> JSON
  python3 scripts/ml/collect_features.py --post <path> --scan-only  # No healer run
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"
SCRIPTS_DIR = REPO_ROOT / "scripts"
ML_DIR = SCRIPTS_DIR / "ml"
OUTPUT_ALL = ML_DIR / "deploy-failure-features.jsonl"
OUTPUT_SINGLE = ML_DIR / "deploy-failure-features.json"

FAILURE_TYPES = [
    "yaml_syntax_in_toml",
    "missing_commit_hash",
    "missing_image",
    "draft_post",
    "wrong_timezone",
    "future_date",
    "insufficient_content",
    "fake_internal_links",
    "dead_image_marker",
    "meta_description_length",
    "hardcoded_footer_section",
    "unused_internal_links",
    "broken_inline_image",
    "attribution_array_of_tables",
    "empty_file",
    "broken_frontmatter",
]

# Patterns from deployment-doctor-knowledge.json used as additional features
_KNOWN_PATTERNS = [
    "Waiting for a runner", "Job is waiting for a hosted runner", "Requested labels: ubuntu-latest",
    "GitHub Status", "Actions delayed starting runs", "Pages builds affected",
    "API rate limit exceeded", "secondary rate limit", "X-RateLimit-Remaining: 0",
    "Pages rate limit", "exceeded the GitHub Pages rate limit", "deployment_rate_limit",
    "concurrency cancelled", "cancel-in-progress", "too many workflows", "workflow fan-out", "fanout",
    "baseline debt", "qa-baseline-debt", "old posts missing image", "MISSING_IMAGE", "MISSING_LICENSE",
    "MISSING_IMAGE", "needs_image", "image_status: needs_image", "No image for slug",
    "No direct_url in manifest", "direct_url", "self-generated", "self_owned", "image_provider = self-generated",
    "VERIFIED_WITHOUT_CREATOR", "creator empty", "source_verified_creator_unavailable",
    "INVALID_IMAGE_CREATOR", "blocked creator", "fake creator",
    "noindex pages incorrectly included in sitemap", "sitemap_noindex_mismatch",
    "Hardcoded absolute paths omit /reviewchanthat/", "baseurl_routing_error",
    "series_hardcoded_url", "Hardcoded /series/ paths",
    "AI summary contains Go map[] serialization artifacts", "ai_summary_map_artifact",
    "QA expects a footer/product element", "qa_expectation_mismatch",
    "Article/table UX regression", "table_layout_ux_regression",
    "Hugo build/render error", "hugo_build_error",
    "Deploy workflow did not complete successfully", "deploy_not_completed",
    "Template/render regression", "template_or_render_regression",
    "Referenced image asset missing", "image_asset_missing",
    "duplicate YAML keys", "duplicate_yaml_keys",
    "Content Direction Optimizer script failed", "content_direction_optimizer_fail",
    "Metadata optimizer", "metadata_optimizer_fail",
]


def parse_frontmatter(content: str) -> Tuple[Optional[str], Optional[str]]:
    match = re.match(r'^\+\+\+\r?\n(.*?)\r?\n\+\+\+', content, re.DOTALL)
    if not match:
        return None, content
    return match.group(1), content[match.end():]


def _git_log(args: List[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, cwd=str(cwd)
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _count_body_elements(body_text: str) -> Dict:
    lines = body_text.splitlines()
    heading_count = sum(1 for l in lines if re.match(r'^#{1,6}\s', l))
    list_count = sum(1 for l in lines if re.match(r'^(\s*[-*+]\s|\s*\d+\.\s)', l))
    table_count = sum(1 for l in lines if '|' in l and l.strip().startswith('|'))
    code_block_count = len(re.findall(r'```', body_text)) // 2
    words = body_text.split()
    avg_paragraph_len = 0
    paragraphs = [p for p in re.split(r'\n\s*\n', body_text) if p.strip()]
    if paragraphs:
        avg_paragraph_len = sum(len(p.split()) for p in paragraphs) / len(paragraphs)
    return {
        "heading_count": heading_count,
        "list_count": list_count,
        "table_count": table_count,
        "code_block_count": code_block_count,
        "paragraph_count": len(paragraphs),
        "avg_paragraph_len": round(avg_paragraph_len, 2),
    }


def _pattern_match_score(text: str) -> int:
    score = 0
    for pat in _KNOWN_PATTERNS:
        if pat.lower() in text.lower():
            score += 1
    return score


def extract_features(filepath: Path, body_text: str, fm_text: str) -> Dict:
    slug = filepath.stem
    title_match = re.search(r'title\s*=\s*"([^"]*)"', fm_text)
    desc_match = re.search(r'description\s*=\s*"([^"]*)"', fm_text)
    tags_match = re.search(r'tags\s*=\s*\[(.*?)\]', fm_text, re.DOTALL)
    cat_match = re.search(r'categories\s*=\s*\[(.*?)\]', fm_text, re.DOTALL)
    draft_match = re.search(r'draft\s*=\s*(true|false)', fm_text)
    date_match = re.search(r'date\s*=\s*"([^"]+)"', fm_text)

    title = title_match.group(1) if title_match else ""
    tags_str = tags_match.group(1) if tags_match else ""
    cats_str = cat_match.group(1) if cat_match else ""
    draft_val = draft_match.group(1) if draft_match else "false"

    cats = re.findall(r'"([^"]+)"', cats_str)
    canonical = ["review", "cong-nghe", "doi-song", "tai-chinh", "du-lich"]
    category_encoded = 0
    for i, c in enumerate(canonical):
        if c in cats:
            category_encoded = i
            break

    ascii_chars = sum(1 for c in title if ord(c) < 128)
    post_lang = "en" if ascii_chars / max(len(title), 1) > 0.8 else "vi"

    inline_image_count = len(re.findall(r'!\[[^\]]*\]\((/?images/posts/[^)]+?\.webp)\)', body_text))
    body_elems = _count_body_elements(body_text)
    pattern_score = _pattern_match_score(title + " " + body_text[:2000])

    # Git metadata
    git_log_args = ["log", "-1", "--format=%h"]
    last_commit = _git_log(git_log_args + ["--", str(filepath)], REPO_ROOT)
    git_count_args = ["log", "--oneline", "--follow", "--", str(filepath)]
    commit_count_str = _git_log(git_count_args, REPO_ROOT)
    commit_count = len([l for l in commit_count_str.splitlines() if l.strip()]) if commit_count_str else 0
    last_commit_ago_days = 0
    last_commit_date_str = _git_log(["log", "-1", "--format=%ci", "--", str(filepath)], REPO_ROOT)
    if last_commit_date_str:
        try:
            lcd = datetime.strptime(last_commit_date_str[:19], "%Y-%m-%d %H:%M:%S")
            last_commit_ago_days = max(0, (datetime.now() - lcd).days)
        except ValueError:
            pass

    features: Dict = {
        "slug": slug,
        "file": str(filepath.relative_to(REPO_ROOT)),
        "word_count": len(body_text.split()),
        "title_len": len(title),
        "slug_len": len(slug),
        "description_len": len(desc_match.group(1)) if desc_match else 0,
        "tag_count": len(re.findall(r'"([^"]+)"', tags_str)),
        "faq_count": len(re.findall(r'^\[\[faq\]\]', fm_text, re.MULTILINE)),
        "external_links_count": len(re.findall(r'^\[\[external_links\]\]', fm_text, re.MULTILINE)),
        "internal_links_count": len(re.findall(r'^\[\[internal_links\]\]', fm_text, re.MULTILINE)),
        "inline_image_count": inline_image_count,
        "heading_count": body_elems["heading_count"],
        "list_count": body_elems["list_count"],
        "table_count": body_elems["table_count"],
        "code_block_count": body_elems["code_block_count"],
        "paragraph_count": body_elems["paragraph_count"],
        "avg_paragraph_len": body_elems["avg_paragraph_len"],
        "known_pattern_score": pattern_score,
        "has_image": 1.0 if re.search(r'image\s*=\s*"[^"]+\.webp"', fm_text) else 0.0,
        "has_thumbnail": 1.0 if re.search(r'thumbnail\s*=\s*"[^"]+\.webp"', fm_text) else 0.0,
        "image_verified": 1.0 if re.search(r'image_status\s*=\s*"verified"', fm_text) else 0.0,
        "image_needs_image": 1.0 if re.search(r'image_status\s*=\s*"needs_image"', fm_text) else 0.0,
        "has_image_creator": 1.0 if re.search(r'image_creator\s*=\s*"[^"]+"', fm_text) else 0.0,
        "has_image_attribution_verified": 1.0 if re.search(r'image_attribution_verified\s*=\s*true', fm_text) else 0.0,
        "has_attribution_single": 1.0 if re.search(r'^\[attribution\]', fm_text, re.MULTILINE) else 0.0,
        "has_attribution_array": 1.0 if re.search(r'^\[\[attribution\]\]', fm_text, re.MULTILINE) else 0.0,
        "has_commit": 1.0 if re.search(r'commit\s*=\s*"[a-f0-9]{7,}"', fm_text) else 0.0,
        "date_has_tz": 1.0 if re.search(r'date\s*=\s*"[^"]+\+07:00"', fm_text) else 0.0,
        "date_is_future": 0.0,
        "has_placeholder_links": 1.0 if re.search(r'/posts/placeholder-', body_text) else 0.0,
        "has_image_api_marker": 1.0 if re.search(r'!\[\[IMAGE_API_QUERY:', body_text) else 0.0,
        "has_yaml_syntax": 1.0 if re.search(r'^\s*(commit|date|image|title|draft|tags|description|categories):\s+', fm_text, re.MULTILINE) else 0.0,
        "category_encoded": float(category_encoded),
        "post_lang_encoded": 1.0 if post_lang == "en" else 0.0,
        "draft": 1.0 if draft_val == "true" else 0.0,
        "has_inline_images": 1.0 if inline_image_count > 0 else 0.0,
        "seo_title_present": 1.0 if re.search(r'seo_title\s*=\s*"', fm_text) else 0.0,
        "lastmod_present": 1.0 if re.search(r'lastmod\s*=\s*"', fm_text) else 0.0,
        "related_posts_count": len(re.findall(r'related_posts\s*=\s*\[(.*?)\]', fm_text, re.DOTALL)),
        "image_query_present": 1.0 if re.search(r'image_query\s*=\s*"', fm_text) else 0.0,
        "git_commit_count": float(commit_count),
        "git_last_commit_ago_days": float(last_commit_ago_days),
    }

    date_match_fm = re.search(r'date\s*=\s*"([^"]+)"', fm_text)
    if date_match_fm:
        try:
            dt = datetime.fromisoformat(date_match_fm.group(1))
            now = datetime.now(timezone.utc).astimezone()
            features["date_is_future"] = 1.0 if dt > now else 0.0
        except ValueError:
            pass

    return features


def extract_labels(filepath: Path, content: str, fm_text: str, body_text: str) -> Dict[str, int]:
    labels = {ft: 0 for ft in FAILURE_TYPES}

    if len(content.strip()) == 0:
        labels["empty_file"] = 1
        return labels

    if not fm_text:
        labels["broken_frontmatter"] = 1
        return labels

    if re.search(r'^\s*(commit|date|image|title|draft|tags|description|categories):\s+', fm_text, re.MULTILINE):
        labels["yaml_syntax_in_toml"] = 1

    if not re.search(r'commit\s*=\s*"[a-f0-9]{7,}"', fm_text):
        labels["missing_commit_hash"] = 1

    if not re.search(r'image\s*=\s*"[^"]+\.webp"', fm_text) or \
       not re.search(r'thumbnail\s*=\s*"[^"]+\.webp"', fm_text):
        labels["missing_image"] = 1

    if re.search(r'draft\s*=\s*true', fm_text):
        labels["draft_post"] = 1

    date_match = re.search(r'date\s*=\s*"([^"]+)"', fm_text)
    if date_match:
        date_str = date_match.group(1)
        if '+07:00' not in date_str:
            labels["wrong_timezone"] = 1
        try:
            dt = datetime.fromisoformat(date_str)
            now = datetime.now(timezone.utc).astimezone()
            if dt > now:
                labels["future_date"] = 1
        except ValueError:
            pass

    if len(body_text.split()) < 3000:
        labels["insufficient_content"] = 1

    if re.search(r'/posts/placeholder-', body_text):
        labels["fake_internal_links"] = 1

    if re.search(r'!\[\[IMAGE_API_QUERY:', body_text):
        labels["dead_image_marker"] = 1

    desc_match = re.search(r'(?m)^description\s*=\s*"(.*)"\s*$', fm_text)
    if desc_match:
        desc_len = len(desc_match.group(1))
        if desc_len < 50 or desc_len > 160:
            labels["meta_description_length"] = 1

    hardcoded_sections = re.findall(
        r'^\s*##\s*(Câu hỏi thường gặp|FAQ|Liên kết nội bộ|Liên kết bên ngoài|Bản quyền|Liên kết được sử dụng)\s*$',
        body_text, re.MULTILINE
    )
    if hardcoded_sections:
        labels["hardcoded_footer_section"] = 1

    import tomllib as _tl
    fm_parsed = re.search(r'^\+{3}\s*$(.*?)^\+{3}\s*$', content, re.MULTILINE | re.DOTALL)
    if fm_parsed:
        try:
            fm_data = _tl.loads(fm_parsed.group(1))
            ilinks = fm_data.get('internal_links', [])
            if ilinks:
                body_text_local = content[fm_parsed.end():]
                unused = 0
                for link in ilinks:
                    ref = link.get('ref', '')
                    title = link.get('title', '')
                    slug = ref.replace('posts/', '').replace('.md', '') if ref else ''
                    tc = re.sub(r'^(Pillar|Series|Bài)\s*:\s*', '', title).strip() if title else ''
                    used = False
                    if ref and (f'](/{ref})' in body_text_local or f']({ref})' in body_text_local):
                        used = True
                    if slug and slug in body_text_local:
                        used = True
                    if len(tc) > 15 and tc in body_text_local:
                        used = True
                    if not used:
                        unused += 1
                if unused > 0:
                    labels["unused_internal_links"] = 1
        except _tl.TOMLDecodeError:
            pass

    for im in re.finditer(r'!\[[^\]]*\]\((/?images/posts/[^)]+?\.webp)\)', body_text):
        ref = im.group(1)
        disk_path = REPO_ROOT / 'static' / ref.lstrip('/')
        if not disk_path.exists():
            labels["broken_inline_image"] = 1
            break

    if re.search(r'^\[\[attribution\]\]', fm_text, re.MULTILINE):
        labels["attribution_array_of_tables"] = 1

    return labels


def collect_post(filepath: Path) -> Optional[Dict]:
    content = filepath.read_text(encoding='utf-8')
    fm_text, body_text = parse_frontmatter(content)
    if fm_text is None:
        fm_text = ""
    features = extract_features(filepath, body_text, fm_text)
    labels = extract_labels(filepath, content, fm_text, body_text)
    return {**features, **labels}


def collect_all() -> List[Dict]:
    records = []
    files = sorted(CONTENT_DIR.rglob("*.md"))
    for fp in files:
        try:
            rec = collect_post(fp)
            if rec:
                records.append(rec)
        except Exception as e:
            print(f"WARNING: failed to process {fp}: {e}", file=sys.stderr)
    return records


def main():
    parser = argparse.ArgumentParser(description="Collect deploy failure features")
    parser.add_argument('--all', action='store_true', help="Collect all posts to JSONL")
    parser.add_argument('--post', type=str, help="Single post path")
    parser.add_argument('--scan-only', action='store_true', help="Skip healer labels, features only")
    args = parser.parse_args()

    if args.all:
        records = collect_all()
        OUTPUT_ALL.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_ALL, 'w', encoding='utf-8') as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        print(f"Collected {len(records)} posts -> {OUTPUT_ALL}")
        return

    if args.post:
        path = Path(args.post)
        if not path.is_absolute():
            path = REPO_ROOT / path
        rec = collect_post(path)
        if rec:
            OUTPUT_SINGLE.parent.mkdir(parents=True, exist_ok=True)
            with open(OUTPUT_SINGLE, 'w', encoding='utf-8') as f:
                json.dump(rec, f, ensure_ascii=False, indent=2)
            print(f"Collected single post -> {OUTPUT_SINGLE}")
        return

    parser.print_help()
    sys.exit(1)


if __name__ == '__main__':
    main()
