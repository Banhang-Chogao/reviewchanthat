import os
import re
from collections import Counter

CONTENT_DIR = "content/posts"
OUTPUT_FILE = "affected_files.txt"

def extract_front_matter(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    parts = content.split('---')
    if len(parts) >= 3:
        return parts[1]
    return None

def find_duplicate_keys(front_matter):
    keys = re.findall(r'^([\w_-]+)\s*:', front_matter, re.MULTILINE)
    key_counts = Counter(keys)
    return {k: v for k, v in key_counts.items() if v > 1}

def main():
    affected = []
    for root, dirs, files in os.walk(CONTENT_DIR):
        for file in files:
            if not file.endswith('.md'):
                continue
            filepath = os.path.join(root, file)
            front_matter = extract_front_matter(filepath)
            if not front_matter:
                continue
            duplicates = find_duplicate_keys(front_matter)
            if duplicates:
                rel_path = os.path.relpath(filepath)
                dup_str = ', '.join(f"{k} (x{v})" for k, v in sorted(duplicates.items()))
                print(f"{rel_path}: {dup_str}")
                affected.append(rel_path)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for path in affected:
            f.write(path + '\n')

    print(f"\nTotal affected files: {len(affected)}")
    print(f"Results saved to: {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
