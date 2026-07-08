"""
scripts/audit_post_images.py
Scan all posts and audit image frontmatter.
Reports: missing, broken, duplicate, missing metadata, valid.
"""

import os
import json
import sys
from collections import defaultdict
import frontmatter

CONTENT_DIR = "content/posts"
REPORT_PATH = "data/image-audit-report.json"
IMAGES_POSTS_DIR = "static/images/posts"

def audit():
    posts_dir = os.path.join(os.getcwd(), CONTENT_DIR)
    if not os.path.exists(posts_dir):
        print(f"ERROR: {CONTENT_DIR} not found")
        sys.exit(1)

    results = []
    image_url_count = defaultdict(list)

    for fname in sorted(os.listdir(posts_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(posts_dir, fname)
        try:
            post = frontmatter.load(fpath)
        except Exception as e:
            results.append({"slug": fname, "status": "parse_error", "error": str(e)})
            continue

        meta = post.metadata
        slug = meta.get("slug", fname.replace(".md", ""))
        title = meta.get("title", slug)
        image = meta.get("image", "")
        thumbnail = meta.get("thumbnail", "")
        image_source = meta.get("image_source", "")
        image_source_url = meta.get("image_source_url", "")
        image_license = meta.get("image_license", "")
        image_commercial_use = meta.get("image_commercial_use", False)
        image_owner = meta.get("image_owner", "")
        tags = meta.get("tags", [])
        categories = meta.get("categories", [])

        issues = []
        status = "valid"

        # Check missing image
        if not image:
            issues.append("missing_image")
            status = "missing_image"

        # Check broken local path
        if image and image.startswith("/"):
            issues.append("broken_image_path_starts_with_slash")
            status = "broken_image_path"

        # Check local file exists if local path
        if image and not image.startswith("http") and not image.startswith("/"):
            local_path = os.path.join(os.getcwd(), "static", image)
            if not os.path.exists(local_path):
                issues.append("local_file_not_found")
                if status == "valid":
                    status = "broken_image_path"

        # Check missing metadata
        missing_meta = []
        if not image_source:
            missing_meta.append("image_source")
        if not image_source_url:
            missing_meta.append("image_source_url")
        if not image_license:
            missing_meta.append("image_license")
        if not image_commercial_use:
            missing_meta.append("image_commercial_use_not_true")
        if not image_owner:
            missing_meta.append("image_owner")

        if missing_meta:
            issues.append(f"missing_metadata:{','.join(missing_meta)}")
            if status == "valid":
                status = "missing_license_metadata"

        # Track duplicate URLs
        if image_source_url:
            image_url_count[image_source_url].append(slug)

        results.append({
            "slug": slug,
            "title": title,
            "status": status,
            "issues": issues,
            "image": image,
            "thumbnail": thumbnail,
            "image_source": image_source,
            "image_source_url": image_source_url,
            "image_license": image_license,
            "image_commercial_use": image_commercial_use,
            "image_owner": image_owner,
            "tags": tags,
            "categories": categories,
        })

    # Mark duplicates
    dupes_found = {}
    for url, slugs in image_url_count.items():
        if len(slugs) > 1:
            for slug in slugs:
                for r in results:
                    if r["slug"] == slug:
                        r["issues"].append(f"duplicate_image:{url}")
                        if r["status"] == "valid":
                            r["status"] = "duplicate_image"
                        break
            dupes_found[url] = slugs

    report = {
        "total_posts": len(results),
        "summary": {
            "valid": sum(1 for r in results if r["status"] == "valid"),
            "missing_image": sum(1 for r in results if r["status"] == "missing_image"),
            "broken_image_path": sum(1 for r in results if r["status"] == "broken_image_path"),
            "missing_license_metadata": sum(1 for r in results if r["status"] == "missing_license_metadata"),
            "duplicate_image": sum(1 for r in results if r["status"] == "duplicate_image"),
        },
        "duplicates": {url: slugs for url, slugs in dupes_found.items()},
        "posts": results,
    }

    os.makedirs("data", exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Audit complete: {REPORT_PATH}")
    print(f"  Total posts: {report['total_posts']}")
    for k, v in report["summary"].items():
        print(f"  {k}: {v}")
    if report["duplicates"]:
        print(f"  Duplicate image URLs: {len(report['duplicates'])}")
        for url, slugs in report["duplicates"].items():
            print(f"    {url}: {len(slugs)} posts")

    return report

if __name__ == "__main__":
    audit()
