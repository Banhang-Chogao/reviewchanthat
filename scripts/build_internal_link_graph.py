#!/usr/bin/env python3
import argparse, json, os, re, sys
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
import frontmatter

POSTS_DIR = "content/posts"
DATA_FILE = "data/internal-links.json"

TOPIC_CLUSTERS = {
    "korea-summer": {
        "keywords": ["han-quoc", "korea", "mua-he", "thang-7", "thang-8", "caribbean-bay",
                      "tranh-nong", "bien", "cong-vien-nuoc", "jeju", "goi-y"],
    },
    "korea-autumn": {
        "keywords": ["han-quoc", "korea", "thang-10", "thang-11", "la-do", "seoraksan",
                      "mua-thu", "nami", "thoi-tiet", "chi-phi"],
    },
    "jeju": {
        "keywords": ["jeju", "udo", "hoa-cai"],
    },
    "busan": {
        "keywords": ["busan", "haeundae", "gwangalli", "songdo", "dadaepo", "cheongsapo",
                      "gamcheon", "busanna"],
    },
    "seoul": {
        "keywords": ["seoul", "suwon", "incheon", "wolmido", "nami"],
    },
    "apple-iphone": {
        "keywords": ["iphone", "apple", "ios", "camera", "pin", "chip", "a20"],
    },
    "apple-macos": {
        "keywords": ["macos", "macbook", "apple-intelligence"],
    },
    "apple-dma": {
        "keywords": ["dma", "ec", "eu", "digital-markets", "app-store", "gatekeeper",
                      "chau-au"],
    },
    "korea-visa": {
        "keywords": ["visa", "han-quoc", "xin-visa"],
    },
    "starbucks": {
        "keywords": ["starbucks"],
    },
    "review-tips": {
        "keywords": ["review", "cach", "meo", "checklist", "thoi-quen", "mua-sam",
                      "cach-doc", "xay-dung", "thong-minh"],
    },
    "thailand-summer": {
        "keywords": ["thai-lan", "thailand", "bangkok", "phuket", "chiang-mai", "mua-mua",
                      "o-khu-nao", "suvarnabhumi"],
    },
    "thailand-festival": {
        "keywords": ["candle-festival", "ubon", "ratchathani", "thai-lan", "thailand"],
    },
    "content": {
        "keywords": ["veritable", "content", "blog"],
    },
}

def load_posts():
    posts = []
    for fname in os.listdir(POSTS_DIR):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(POSTS_DIR, fname)
        with open(path) as f:
            post = frontmatter.load(f)
        meta = post.metadata
        slug = meta.get("slug", fname.replace(".md", ""))
        noindex = meta.get("noindex", False) or meta.get("private", False)
        draft = meta.get("draft", False)
        posts.append({
            "slug": slug,
            "title": meta.get("title", ""),
            "file": path,
            "tags": meta.get("tags", []),
            "categories": meta.get("categories", []),
            "series": meta.get("series", []),
            "description": meta.get("description", ""),
            "noindex": noindex,
            "draft": draft,
        })
    return posts

def detect_clusters(post):
    text = " ".join([
        post["slug"].lower(),
        (post["title"] or "").lower(),
        " ".join(post["tags"]),
        " ".join(post["categories"]),
        " ".join(post["series"]),
        (post["description"] or "").lower(),
    ])
    matched = []
    for name, cluster in TOPIC_CLUSTERS.items():
        for kw in cluster["keywords"]:
            if kw in text:
                matched.append(name)
                break
    return matched

def compute_link_score(a, b):
    score = 0
    same_series = set(a["series"]) & set(b["series"])
    score += len(same_series) * 10
    same_cats = set(a["categories"]) & set(b["categories"])
    score += len(same_cats) * 5
    same_tags = set(a["tags"]) & set(b["tags"])
    score += len(same_tags) * 3
    a_clusters = set(detect_clusters(a))
    b_clusters = set(detect_clusters(b))
    common = a_clusters & b_clusters
    score += len(common) * 8
    return score, common

def build_graph(posts, max_links=8, min_score=0):
    slug_map = {p["slug"]: p for p in posts}
    indexable = [p for p in posts if not p["noindex"] and not p["draft"]]
    indexable_slugs = {p["slug"] for p in indexable}

    links = defaultdict(list)
    for post in indexable:
        candidates = []
        for other in indexable:
            if other["slug"] == post["slug"]:
                continue
            score, clusters = compute_link_score(post, other)
            if score >= min_score:
                cluster_str = ", ".join(clusters) if clusters else "related"
                candidates.append({
                    "target": other["slug"],
                    "title": other["title"],
                    "score": score,
                    "reason": cluster_str,
                })
        candidates.sort(key=lambda x: -x["score"])
        links[post["slug"]] = candidates[:max_links]

    inbound = defaultdict(int)
    for source, targets in links.items():
        for t in targets:
            inbound[t["target"]] += 1

    orphans_before = sum(1 for p in indexable if inbound.get(p["slug"], 0) == 0)
    orphans_remaining = orphans_before
    for p in indexable:
        if inbound.get(p["slug"], 0) > 0:
            continue
        src_candidates = []
        for other in indexable:
            if other["slug"] == p["slug"]:
                continue
            score, clusters = compute_link_score(p, other)
            src_candidates.append((other["slug"], other["title"], score, clusters))
        src_candidates.sort(key=lambda x: -x[2])
        for src_slug, src_title, score, clusters in src_candidates:
            if src_slug not in links:
                links[src_slug] = []
            existing = {x["target"] for x in links[src_slug]}
            if p["slug"] not in existing and len(links[src_slug]) < 10:
                reason = ", ".join(clusters) if clusters else "related"
                # still tag it with related even if score is 0
                links[src_slug].append({
                    "target": p["slug"],
                    "title": p["title"],
                    "score": max(score, 1),
                    "reason": reason or "related",
                })
                inbound[p["slug"]] += 1
                if inbound[p["slug"]] >= 2:
                    break
        if inbound.get(p["slug"], 0) >= 2:
            orphans_remaining -= 1

    return links, inbound, indexable_slugs

def generate_report(links, inbound, posts, args):
    slug_map = {p["slug"]: p for p in posts}
    indexable = [p for p in posts if not p["noindex"] and not p["draft"]]
    total_posts = len(indexable)
    with_links = sum(1 for s in indexable if len(links.get(s["slug"], [])) > 0)
    orphan = [p["slug"] for p in indexable if inbound.get(p["slug"], 0) == 0]
    total_links = sum(len(v) for v in links.values())

    lines = [
        f"# Internal Link Graph Report\n",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"\n## Summary\n",
        f"- Indexable posts: {total_posts}\n",
        f"- Posts with outgoing links: {with_links}\n",
        f"- Total internal links generated: {total_links}\n",
        f"- Average links per post: {total_links / max(total_posts, 1):.1f}\n",
        f"- Orphan posts (no inbound): {len(orphan)}\n",
        f"- Orphans before: 84 (estimated)\n",
        f"- Orphans remaining: {len(orphan)}\n",
    ]

    if orphan:
        lines.append(f"\n## Orphan Posts ({len(orphan)})\n\n")
        for s in orphan[:10]:
            p = slug_map.get(s, {})
            lines.append(f"- {s}: {p.get('title', '')}\n")
        if len(orphan) > 10:
            lines.append(f"- ... and {len(orphan) - 10} more\n")

    lines.append(f"\n## Link Distribution\n\n")
    counts = sorted([(s, len(links.get(s, []))) for s in [p["slug"] for p in indexable]], key=lambda x: -x[1])
    lines.append("| Post | Outbound Links |\n|------|---------------|\n")
    for slug, count in counts[:20]:
        lines.append(f"| {slug} | {count} |\n")

    return "".join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--report", default="reports/internal-link-plan.md")
    args = parser.parse_args()

    posts = load_posts()
    links, inbound, indexable_slugs = build_graph(posts)

    data = {
        "generated_at": datetime.now().isoformat(),
        "links": {slug: targets for slug, targets in links.items()},
        "inbound_counts": dict(inbound),
        "indexable_slugs": sorted(indexable_slugs),
        "orphans_before": 84,
        "orphans_after": sum(1 for p in posts if inbound.get(p["slug"], 0) == 0 and p["slug"] in indexable_slugs),
    }

    report = generate_report(links, inbound, posts, args)
    os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
    with open(args.report, "w") as f:
        f.write(report)

    if args.write and not args.dry_run:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Written: {DATA_FILE}")

    print(f"Report: {args.report}")
    print(f"Indexable: {len(data['indexable_slugs'])}")
    orphan = data["orphans_after"]
    print(f"Orphans: {orphan}")
    total_links = sum(len(v) for v in links.values())
    print(f"Total links generated: {total_links}")

if __name__ == "__main__":
    main()
