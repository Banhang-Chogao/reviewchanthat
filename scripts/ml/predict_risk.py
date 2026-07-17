#!/usr/bin/env python3
"""
Deploy Failure Risk Predictor
==============================
Predicts deploy failure risk for a single blog post using the trained ML model.
Handles degenerate labels (no positive samples) gracefully.

Usage:
  python3 scripts/ml/predict_risk.py --post content/posts/<slug>.md
  python3 scripts/ml/predict_risk.py --post content/posts/<slug>.md --threshold 0.3
  python3 scripts/ml/predict_risk.py --post content/posts/<slug>.md --json
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import joblib
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ML_DIR = Path(__file__).resolve().parent
MODEL_PATH = ML_DIR / "deploy_failure_model.joblib"
METADATA_PATH = ML_DIR / "model_metadata.json"

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

FEATURE_COLS = [
    "word_count",
    "title_len",
    "slug_len",
    "description_len",
    "tag_count",
    "faq_count",
    "external_links_count",
    "internal_links_count",
    "inline_image_count",
    "heading_count",
    "list_count",
    "table_count",
    "code_block_count",
    "paragraph_count",
    "avg_paragraph_len",
    "known_pattern_score",
    "has_image",
    "has_thumbnail",
    "image_verified",
    "image_needs_image",
    "has_image_creator",
    "has_image_attribution_verified",
    "has_attribution_single",
    "has_attribution_array",
    "has_commit",
    "date_has_tz",
    "date_is_future",
    "has_placeholder_links",
    "has_image_api_marker",
    "has_yaml_syntax",
    "category_encoded",
    "post_lang_encoded",
    "draft",
    "has_inline_images",
    "seo_title_present",
    "lastmod_present",
    "related_posts_count",
    "image_query_present",
    "git_commit_count",
    "git_last_commit_ago_days",
]

ACTION_MAP = {
    "yaml_syntax_in_toml": "Chạy: python3 scripts/rule.py --fix --post <slug>",
    "missing_commit_hash": "Chạy: python3 scripts/add_commit_id.py --post <slug>",
    "missing_image": "Chạy: python3 scripts/select_images.py --post <slug> --fix",
    "draft_post": "Đổi draft = false hoặc remove khỏi deploy",
    "wrong_timezone": "Chạy: python3 scripts/qa_dates.py --post <slug> --fix-obvious",
    "future_date": "Chạy: python3 scripts/qa_dates.py --post <slug> --fix-obvious",
    "insufficient_content": "Mở rộng nội dung lên >= 3000 từ",
    "fake_internal_links": "Xóa link /posts/placeholder-*",
    "dead_image_marker": "Xóa ![[IMAGE_API_QUERY:...]] markers",
    "meta_description_length": "Viết lại description 50-160 ký tự",
    "hardcoded_footer_section": "Chạy: python3 scripts/move_hardcoded_footer_sections.py --fix --post <slug>",
    "unused_internal_links": "Chạy: python3 scripts/strip_unused_internal_links.py --write --post <slug>",
    "broken_inline_image": "Tạo lại webp hoặc xóa ![]() bị lỗi",
    "attribution_array_of_tables": "Đổi [[attribution]] -> [attribution] trong front matter",
    "empty_file": "Xóa file rỗng",
    "broken_frontmatter": "Sửa front matter TOML đúng format +++...+++",
}


def parse_frontmatter(content: str):
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
    paragraphs = [p for p in re.split(r'\n\s*\n', body_text) if p.strip()]
    avg_paragraph_len = 0
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

    known_patterns = [
        "Waiting for a runner", "Job is waiting for a hosted runner", "Requested labels: ubuntu-latest",
        "GitHub Status", "Actions delayed starting runs", "Pages builds affected",
        "API rate limit exceeded", "secondary rate limit", "X-RateLimit-Remaining: 0",
        "Pages rate limit", "exceeded the GitHub Pages rate limit", "deployment_rate_limit",
        "concurrency cancelled", "cancel-in-progress", "too many workflows", "workflow fan-out", "fanout",
        "baseline debt", "qa-baseline-debt", "old posts missing image", "MISSING_IMAGE", "MISSING_LICENSE",
        "needs_image", "image_status: needs_image", "No image for slug",
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
    pattern_score = sum(1 for p in known_patterns if p.lower() in (title + " " + body_text[:2000]).lower())

    last_commit = _git_log(["log", "-1", "--format=%h", "--", str(filepath)], REPO_ROOT)
    commit_count_str = _git_log(["log", "--oneline", "--follow", "--", str(filepath)], REPO_ROOT)
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

    if date_match:
        try:
            dt = datetime.fromisoformat(date_match.group(1))
            now = datetime.now(timezone.utc).astimezone()
            features["date_is_future"] = 1.0 if dt > now else 0.0
        except ValueError:
            pass

    return features


def predict(filepath: Path, threshold: float = 0.35) -> Dict:
    content = filepath.read_text(encoding='utf-8')
    fm_text, body_text = parse_frontmatter(content)
    if fm_text is None:
        fm_text = ""

    features = extract_features(filepath, body_text, fm_text)
    X = pd.DataFrame([{k: features[k] for k in FEATURE_COLS}])

    model = joblib.load(MODEL_PATH)
    meta = json.loads(METADATA_PATH.read_text(encoding='utf-8'))

    # Identify labels with no positive samples in training (degenerate)
    train_counts = meta.get("train_label_counts", {})
    valid_labels = [l for l in FAILURE_TYPES if train_counts.get(l, 0) > 0]

    proba = model.predict_proba(X)
    preds = {}
    risks = []
    skipped = []

    for i, label in enumerate(FAILURE_TYPES):
        if label not in valid_labels:
            skipped.append(label)
            continue
        arr = proba[i]
        if hasattr(arr, 'shape') and len(arr.shape) == 2 and arr.shape[1] == 2:
            pos_proba = float(arr[0, 1])
        else:
            pos_proba = float(arr.flat[0]) if hasattr(arr, 'flat') else float(arr[0])
        preds[label] = round(pos_proba, 4)
        if pos_proba >= threshold:
            risks.append({
                "failure_type": label,
                "probability": round(pos_proba, 4),
                "action": ACTION_MAP.get(label, "Review manually"),
            })

    risks.sort(key=lambda x: x["probability"], reverse=True)
    overall_risk = float(max(preds.values())) if preds else 0.0

    return {
        "slug": filepath.stem,
        "file": str(filepath.relative_to(REPO_ROOT)),
        "overall_risk": round(overall_risk, 4),
        "threshold": threshold,
        "flagged_count": len(risks),
        "risks": risks,
        "skipped_labels": skipped,
        "all_probabilities": preds,
        "model_hamming_loss": meta.get("hamming_loss"),
        "trained_at": meta.get("trained_at"),
        "n_samples_trained": meta.get("n_samples"),
    }


def main():
    parser = argparse.ArgumentParser(description="Predict deploy failure risk")
    parser.add_argument('--post', type=str, required=True, help="Post path")
    parser.add_argument('--threshold', type=float, default=0.35)
    parser.add_argument('--json', action='store_true', help="Output raw JSON")
    args = parser.parse_args()

    path = Path(args.post)
    if not path.is_absolute():
        path = REPO_ROOT / path

    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)

    if not MODEL_PATH.exists():
        print(f"ERROR: Model not found at {MODEL_PATH}. Run train_model.py first.", file=sys.stderr)
        sys.exit(1)

    result = predict(path, threshold=args.threshold)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"\n🔍 Deploy Risk Prediction: {result['slug']}")
    print(f"   File: {result['file']}")
    print(f"   Overall risk: {result['overall_risk']:.1%}")
    print(f"   Threshold: {result['threshold']:.1%}")
    print(f"   Flagged issues: {result['flagged_count']}")
    if result.get('skipped_labels'):
        print(f"   Skipped labels (no training data): {', '.join(result['skipped_labels'])}")
    print(f"   Model trained on: {result['n_samples_trained']} samples (hamming_loss={result['model_hamming_loss']})")

    if result['risks']:
        print("\n⚠️  Recommended fixes (ordered by probability):")
        for r in result['risks']:
            print(f"   [{r['probability']:.1%}] {r['failure_type']}")
            print(f"         -> {r['action'].replace('<slug>', result['slug'])}")
    else:
        print("\n✅ No high-risk issues detected.")


if __name__ == '__main__':
    main()
