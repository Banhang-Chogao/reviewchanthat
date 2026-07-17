#!/usr/bin/env python3
"""
Deploy Failure Model Trainer
=============================
Trains a multi-label RandomForest classifier on deploy failure features.

Usage:
  python3 scripts/ml/train_model.py --features scripts/ml/deploy-failure-features.jsonl
  python3 scripts/ml/train_model.py --features scripts/ml/deploy-failure-features.jsonl --test-size 0.2
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, hamming_loss
from datetime import datetime, timezone

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


def load_features(path: Path) -> pd.DataFrame:
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return pd.DataFrame(rows)


def train(df: pd.DataFrame, test_size: float = 0.2) -> Tuple[MultiOutputClassifier, Dict]:
    X = df[FEATURE_COLS].astype(float)
    y = df[FAILURE_TYPES].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=None
    )

    base_clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=42,
    )
    model = MultiOutputClassifier(base_clf, n_jobs=-1)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, target_names=FAILURE_TYPES, zero_division=0, output_dict=True)
    hl = hamming_loss(y_test, y_pred)

    importances = np.zeros(len(FEATURE_COLS))
    for est in model.estimators_:
        importances += est.feature_importances_
    importances /= len(model.estimators_)

    feat_imp = sorted(
        [{"feature": f, "importance": round(float(v), 6)} for f, v in zip(FEATURE_COLS, importances)],
        key=lambda x: x["importance"],
        reverse=True,
    )

    metadata = {
        "trained_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "n_samples": len(df),
        "n_features": len(FEATURE_COLS),
        "n_labels": len(FAILURE_TYPES),
        "test_size": test_size,
        "hamming_loss": round(float(hl), 6),
        "feature_importances": feat_imp,
        "labels": FAILURE_TYPES,
        "features": FEATURE_COLS,
        "train_label_counts": {k: int(v) for k, v in df[FAILURE_TYPES].sum().items()},
        "per_label_f1": {k: round(v.get("f1-score", 0.0), 4) for k, v in report.items() if k in FAILURE_TYPES},
    }

    return model, metadata


def main():
    parser = argparse.ArgumentParser(description="Train deploy failure risk model")
    parser.add_argument('--features', type=str, default=str(REPO_ROOT / "scripts" / "ml" / "deploy-failure-features.jsonl"))
    parser.add_argument('--test-size', type=float, default=0.2)
    parser.add_argument('--output-model', type=str, default=str(MODEL_PATH))
    parser.add_argument('--output-metadata', type=str, default=str(METADATA_PATH))
    args = parser.parse_args()

    print(f"Loading features from {args.features}...")
    df = load_features(Path(args.features))
    print(f"Loaded {len(df)} posts, {len(FAILURE_TYPES)} failure types.")

    if len(df) < 10:
        print("ERROR: Need at least 10 samples to train.", file=sys.stderr)
        sys.exit(1)

    print("\nLabel distribution:")
    for col in FAILURE_TYPES:
        count = int(df[col].sum())
        pct = count / len(df) * 100
        print(f"  {col}: {count} ({pct:.1f}%)")

    print("\nTraining model...")
    model, metadata = train(df, test_size=args.test_size)

    print(f"\nHamming loss: {metadata['hamming_loss']}")
    print("\nPer-label F1 (test set):")
    for label, f1 in metadata["per_label_f1"].items():
        print(f"  {label}: {f1:.3f}")

    joblib.dump(model, args.output_model)
    with open(args.output_metadata, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\nModel saved -> {args.output_model}")
    print(f"Metadata saved -> {args.output_metadata}")


if __name__ == '__main__':
    main()
