"""
Normalize image attribution data without inventing creator names.

The manifest is treated as the only local record of provider API creator metadata.
If it has no creator, post front matter is written with an empty image_creator.
"""

import json
import os
import re
import sys

CONTENT_DIR = "content/posts"
IMAGES_MANIFEST_PATH = "data/images.json"
SOURCE_CACHE_PATH = "data/image-source-cache.json"

BLOCKED_CREATOR_NAMES = {
    "park bogum",
    "park bo-gum",
    "bae suzy",
    "iu",
    "yoo jaesuk",
    "choi wooshik",
    "lee minho",
    "lee min ho",
    "kim soo hyun",
    "song hye kyo",
}

BLOCKED_CREATOR_PHRASES = {
    "unknown photographer",
    "photographer unknown",
    "unknown creator",
    "creator unknown",
    "placeholder",
}


def clean_text(value):
    if isinstance(value, str):
        return value.strip()
    return ""


def normalized(value):
    return " ".join(clean_text(value).casefold().split())


def is_blocked_creator(value):
    value_norm = normalized(value)
    if not value_norm:
        return False
    if value_norm in BLOCKED_CREATOR_NAMES:
        return True
    return any(phrase in value_norm for phrase in BLOCKED_CREATOR_PHRASES)


def attribution_text(platform, creator):
    platform = clean_text(platform)
    creator = clean_text(creator)
    if not platform:
        return ""
    if creator:
        return f"Source: {platform} / {creator}"
    return f"Source: {platform}"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def normalize_entry(entry):
    if not isinstance(entry, dict):
        return False
    before = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    creator = clean_text(entry.get("creator"))
    if is_blocked_creator(creator):
        creator = ""
    entry["creator"] = creator
    entry["creator_url"] = clean_text(entry.get("creator_url")) if creator else ""
    entry["watermark_text"] = attribution_text(entry.get("source_platform"), creator)
    after = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    return before != after


def load_manifest():
    if not os.path.exists(IMAGES_MANIFEST_PATH):
        print(f"ERROR: {IMAGES_MANIFEST_PATH} not found")
        sys.exit(1)
    manifest = load_json(IMAGES_MANIFEST_PATH, {"posts": []})
    changed = 0
    for entry in manifest.get("posts", []):
        if normalize_entry(entry):
            changed += 1
    return manifest, changed


def normalize_source_cache():
    cache = load_json(SOURCE_CACHE_PATH, {})
    changed = 0
    if isinstance(cache, dict):
        for entry in cache.values():
            if normalize_entry(entry):
                changed += 1
    return cache, changed


def split_front_matter(text):
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None, None, None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return lines[:1], lines[1:idx], lines[idx:]
    return None, None, None


def strip_yaml_scalar(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def get_scalar(lines, key):
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.*)$")
    for line in lines:
        match = pattern.match(line.rstrip("\n"))
        if match:
            return strip_yaml_scalar(match.group(1))
    return ""


def yaml_scalar(value):
    value = clean_text(value)
    if not value:
        return '""'
    if re.search(r'[:#\[\]{}"]|^\s|\s$|^[-?]', value):
        return json.dumps(value, ensure_ascii=False)
    return value


def set_scalar(lines, key, value):
    rendered = f"{key}: {yaml_scalar(value)}\n"
    pattern = re.compile(rf"^{re.escape(key)}:\s*")
    for idx, line in enumerate(lines):
        if pattern.match(line):
            if line != rendered:
                lines[idx] = rendered
                return True
            return False

    anchors = [
        "image_creator",
        "image_owner",
        "image_source_url",
        "image_source",
        "thumbnail",
        "image",
    ]
    insert_at = len(lines)
    for anchor in anchors:
        anchor_pattern = re.compile(rf"^{re.escape(anchor)}:\s*")
        for idx, line in enumerate(lines):
            if anchor_pattern.match(line):
                insert_at = idx + 1
                break
        if insert_at != len(lines):
            break
    lines.insert(insert_at, rendered)
    return True


def update_post_file(path, manifest_by_slug):
    with open(path, encoding="utf-8") as f:
        original = f.read()

    prefix, front_lines, suffix = split_front_matter(original)
    if front_lines is None:
        return False, "no_front_matter"

    fname = os.path.basename(path)
    slug = clean_text(get_scalar(front_lines, "slug")) or fname.removesuffix(".md")
    image_source = clean_text(get_scalar(front_lines, "image_source"))
    image_source_url = clean_text(get_scalar(front_lines, "image_source_url"))
    current_creator = clean_text(get_scalar(front_lines, "image_creator"))

    if not image_source and not image_source_url and not current_creator:
        return False, "no_image_metadata"

    entry = manifest_by_slug.get(slug)
    if entry:
        creator = clean_text(entry.get("creator"))
        creator_url = clean_text(entry.get("creator_url")) if creator else ""
    else:
        creator = "" if is_blocked_creator(current_creator) else current_creator
        creator_url = clean_text(get_scalar(front_lines, "image_creator_url")) if creator else ""

    changed = False
    changed |= set_scalar(front_lines, "image_creator", creator)
    changed |= set_scalar(front_lines, "image_creator_url", creator_url)

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write("".join(prefix + front_lines + suffix))
        return True, "updated"
    return False, "unchanged"


def main():
    print("=== Normalize Image Attribution ===")
    manifest, manifest_changed = load_manifest()
    manifest_by_slug = {
        clean_text(entry.get("slug")): entry
        for entry in manifest.get("posts", [])
        if clean_text(entry.get("slug"))
    }

    cache, cache_changed = normalize_source_cache()

    post_changed = 0
    post_skipped = 0
    for fname in sorted(os.listdir(CONTENT_DIR)):
        if not fname.endswith(".md"):
            continue
        changed, _reason = update_post_file(os.path.join(CONTENT_DIR, fname), manifest_by_slug)
        if changed:
            post_changed += 1
        else:
            post_skipped += 1

    if manifest_changed:
        save_json(IMAGES_MANIFEST_PATH, manifest)
    if cache_changed:
        save_json(SOURCE_CACHE_PATH, cache)

    print(f"  Manifest entries normalized: {manifest_changed}")
    print(f"  Source cache entries normalized: {cache_changed}")
    print(f"  Post front matters updated: {post_changed}")
    print(f"  Post front matters unchanged/skipped: {post_skipped}")


if __name__ == "__main__":
    main()
