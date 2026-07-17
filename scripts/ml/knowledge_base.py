#!/usr/bin/env python3
"""
Deploy Failure Knowledge Base
==============================
Merges deploy-failure doctor data, healer scan results, and ML model metadata
into a single knowledge base used for pre-deploy risk assessment and fix recommendation.

Usage:
  python3 scripts/ml/knowledge_base.py --build
  python3 scripts/ml/knowledge_base.py --query <failure_type>
  python3 scripts/ml/knowledge_base.py --stats
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ML_DIR = Path(__file__).resolve().parent
KB_PATH = ML_DIR / "deploy_failure_knowledge.json"


def load_json(path: Path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def build():
    doctor = load_json(REPO_ROOT / "data" / "deployment-doctor.json")
    knowledge = load_json(REPO_ROOT / "data" / "deployment-doctor-knowledge.json")
    attempts = load_json(REPO_ROOT / "data" / "deployment-doctor-attempts.json")
    baseline = load_json(REPO_ROOT / "data" / "qa-baseline-debt.json")
    meta_path = ML_DIR / "model_metadata.json"
    model_meta = load_json(meta_path) if meta_path.exists() else {}

    kb = {
        "built_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "sources": {
            "deployment_doctor": str(REPO_ROOT / "data" / "deployment-doctor.json"),
            "knowledge": str(REPO_ROOT / "data" / "deployment-doctor-knowledge.json"),
            "attempts": str(REPO_ROOT / "data" / "deployment-doctor-attempts.json"),
            "baseline_debt": str(REPO_ROOT / "data" / "qa-baseline-debt.json"),
            "model_metadata": str(meta_path),
        },
        "summary": doctor.get("summary", {}),
        "lessons_learned": knowledge.get("lessons_learned", []),
        "patterns": knowledge.get("patterns", []),
        "recent_failures": doctor.get("recent_failures", []),
        "autofix_history": doctor.get("autofix_history", []),
        "loop_guarded": doctor.get("loop_guarded", []),
        "action_items": doctor.get("action_items", []),
        "baseline_debt": baseline.get("known_issues", {}),
        "model": {
            "trained_at": model_meta.get("trained_at"),
            "n_samples": model_meta.get("n_samples"),
            "hamming_loss": model_meta.get("hamming_loss"),
            "labels": model_meta.get("labels", []),
            "features": model_meta.get("features", []),
            "train_label_counts": model_meta.get("train_label_counts", {}),
            "feature_importances": model_meta.get("feature_importances", []),
        },
    }

    KB_PATH.parent.mkdir(parents=True, exist_ok=True)
    KB_PATH.write_text(json.dumps(kb, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Knowledge base built -> {KB_PATH}")
    return kb


def query(failure_type: str):
    kb = load_json(KB_PATH)
    if not kb:
        print("Knowledge base not found. Run --build first.", file=sys.stderr)
        sys.exit(1)

    matches = []
    for p in kb.get("patterns", []):
        if p.get("id") == failure_type or failure_type.lower() in [m.lower() for m in p.get("match", [])]:
            matches.append(p)

    for f in kb.get("recent_failures", []):
        if f.get("rootcause") == failure_type:
            matches.append({"type": "recent_failure", "data": f})

    for a in kb.get("action_items", []):
        if a.get("failure_type") == failure_type:
            matches.append({"type": "action_item", "data": a})

    if not matches:
        print(f"No knowledge found for: {failure_type}")
        return

    print(f"\n📚 Knowledge for: {failure_type}")
    for m in matches:
        if "summary" in m:
            print(f"  Pattern: {m.get('id')}")
            print(f"    Severity: {m.get('severity')}")
            print(f"    Summary: {m.get('summary')}")
            print(f"    Safe to autofix: {m.get('safe_to_autofix')}")
            if m.get('action_items'):
                print(f"    Action items: {'; '.join(m['action_items'])}")
            if m.get('recommended_fix_script'):
                print(f"    Fix script: {m['recommended_fix_script']}")
        elif m.get("type") == "recent_failure":
            d = m["data"]
            print(f"  Recent failure: run {d.get('run_id')} ({d.get('workflow')})")
            print(f"    Root cause: {d.get('rootcause')}")
            print(f"    Action: {d.get('action')}")
        elif m.get("type") == "action_item":
            d = m["data"]
            print(f"  Action item: {d.get('title')}")
            print(f"    Priority: {d.get('priority')}")
            print(f"    Expected: {d.get('expected_result')}")


def stats():
    kb = load_json(KB_PATH)
    if not kb:
        print("Knowledge base not found. Run --build first.", file=sys.stderr)
        sys.exit(1)

    print("\n📊 Knowledge Base Stats")
    print(f"  Built at: {kb.get('built_at')}")
    print(f"  Patterns: {len(kb.get('patterns', []))}")
    print(f"  Lessons learned: {len(kb.get('lessons_learned', []))}")
    print(f"  Recent failures: {len(kb.get('recent_failures', []))}")
    print(f"  Autofix history: {len(kb.get('autofix_history', []))}")
    print(f"  Loop guarded: {len(kb.get('loop_guarded', []))}")
    print(f"  Action items: {len(kb.get('action_items', []))}")
    print(f"  Baseline debt items: {len(kb.get('baseline_debt', {}))}")
    model = kb.get('model', {})
    print(f"  Model samples: {model.get('n_samples')}")
    print(f"  Model hamming_loss: {model.get('hamming_loss')}")
    print(f"  Model labels: {len(model.get('labels', []))}")


def main():
    parser = argparse.ArgumentParser(description="Deploy Failure Knowledge Base")
    parser.add_argument('--build', action='store_true', help="Build knowledge base from sources")
    parser.add_argument('--query', type=str, help="Query knowledge by failure type")
    parser.add_argument('--stats', action='store_true', help="Show knowledge base statistics")
    args = parser.parse_args()

    if args.build:
        build()
        return
    if args.query:
        query(args.query)
        return
    if args.stats:
        stats()
        return

    parser.print_help()
    sys.exit(1)


if __name__ == '__main__':
    main()
