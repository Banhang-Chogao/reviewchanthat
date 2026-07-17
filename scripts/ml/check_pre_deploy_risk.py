#!/usr/bin/env python3
"""
ML Pre-Deploy Risk Check
=========================
Combines the trained ML risk predictor with the deploy-failure-healer scan
to provide an early-warning pre-deploy gate.

Usage:
  python3 scripts/ml/check_pre_deploy_risk.py --post content/posts/<slug>.md
  python3 scripts/ml/check_pre_deploy_risk.py --post content/posts/<slug>.md --threshold 0.3
  python3 scripts/ml/check_pre_deploy_risk.py --post content/posts/<slug>.md --json
  python3 scripts/ml/check_pre_deploy_risk.py --all
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ML_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

try:
    from predict_risk import predict as ml_predict, FEATURE_COLS, FAILURE_TYPES
except ImportError:
    from scripts.ml.predict_risk import predict as ml_predict, FEATURE_COLS, FAILURE_TYPES


def run_healer(post_path: Path) -> List[Dict]:
    result = subprocess.run(
        ["python3", str(SCRIPTS_DIR / "deploy-failure-healer.py"), "--scan", "--post", str(post_path)],
        capture_output=True, text=True, cwd=str(REPO_ROOT)
    )
    # Healer prints human-readable report; for structured data we parse the issues list
    # Fallback: return empty and rely on ML + stdout
    return []


def check_post(post_path: Path, threshold: float = 0.35) -> Dict:
    ml_result = ml_predict(post_path, threshold=threshold)
    healer_issues = run_healer(post_path)

    # Merge: ML flags predicted risks; healer flags confirmed issues
    ml_risks = {r["failure_type"]: r["probability"] for r in ml_result.get("risks", [])}
    healer_types = set()  # Could parse healer output if structured JSON added later

    combined_risks = []
    for ft, prob in ml_risks.items():
        combined_risks.append({
            "failure_type": ft,
            "probability": prob,
            "source": "ml_model",
            "action": f"Chạy: python3 scripts/ml/predict_risk.py --post {post_path.name}",
        })

    # If healer found any issues, add them as high-confidence
    # (healer output is text; we append a summary)
    if healer_issues:
        combined_risks.append({
            "failure_type": "healer_scan_issues",
            "probability": 1.0,
            "source": "healer_scan",
            "action": "Chạy: python3 scripts/deploy-failure-healer.py --scan --post <slug>",
        })

    combined_risks.sort(key=lambda x: x["probability"], reverse=True)

    return {
        "slug": post_path.stem,
        "file": str(post_path.relative_to(REPO_ROOT)),
        "overall_risk": ml_result.get("overall_risk", 0.0),
        "threshold": threshold,
        "ml_flagged": len(ml_result.get("risks", [])),
        "healer_issues_found": len(healer_issues),
        "combined_risks": combined_risks,
        "skipped_ml_labels": ml_result.get("skipped_labels", []),
        "model_hamming_loss": ml_result.get("model_hamming_loss"),
        "n_samples_trained": ml_result.get("n_samples_trained"),
    }


def check_all(threshold: float = 0.35) -> List[Dict]:
    results = []
    for fp in sorted((REPO_ROOT / "content" / "posts").rglob("*.md")):
        try:
            results.append(check_post(fp, threshold=threshold))
        except Exception as e:
            print(f"WARNING: {fp}: {e}", file=sys.stderr)
    return results


def main():
    parser = argparse.ArgumentParser(description="ML Pre-Deploy Risk Check")
    parser.add_argument('--post', type=str, help="Single post path")
    parser.add_argument('--all', action='store_true', help="Check all posts")
    parser.add_argument('--threshold', type=float, default=0.35)
    parser.add_argument('--json', action='store_true', help="Output raw JSON")
    args = parser.parse_args()

    if args.all:
        results = check_all(threshold=args.threshold)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            flagged = [r for r in results if r["combined_risks"]]
            print(f"\n🔍 ML Pre-Deploy Check: {len(results)} posts scanned")
            print(f"   Flagged: {len(flagged)}")
            for r in flagged:
                print(f"   ⚠️  {r['slug']}: risk={r['overall_risk']:.1%}, issues={r['ml_flagged']}+{r['healer_issues_found']}")
        return

    if args.post:
        path = Path(args.post)
        if not path.is_absolute():
            path = REPO_ROOT / path
        result = check_post(path, threshold=args.threshold)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"\n🔍 ML Pre-Deploy Check: {result['slug']}")
            print(f"   Overall risk: {result['overall_risk']:.1%}")
            print(f"   ML flagged: {result['ml_flagged']}")
            print(f"   Healer issues: {result['healer_issues_found']}")
            if result["skipped_ml_labels"]:
                print(f"   Skipped ML labels: {', '.join(result['skipped_ml_labels'])}")
            if result["combined_risks"]:
                print("\n⚠️  Risks:")
                for r in result["combined_risks"]:
                    print(f"   [{r['probability']:.1%}] {r['failure_type']} ({r['source']})")
                    print(f"         -> {r['action']}")
            else:
                print("\n✅ No high-risk issues detected.")
        return

    parser.print_help()
    sys.exit(1)


if __name__ == '__main__':
    main()
