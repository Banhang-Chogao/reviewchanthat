#!/usr/bin/env python3
"""
Fix internal link refs that point to old filenames after the 56513c3 migration.
Replaces old filename refs with new filenames in both internal_links front
matter ref: values and {{< ref "..." >}} body shortcodes.
"""
import os
import re
import subprocess

POSTS_DIR = "content/posts"

def get_rename_map():
    """Build old->new filename map from git rename info."""
    result = subprocess.run(
        ['git', 'show', 'f99bbfd', '--diff-filter=R', '--name-status', '--', 'content/posts/'],
        capture_output=True, text=True
    )
    rename_map = {}
    for line in result.stdout.strip().split('\n'):
        if line.startswith('R'):
            parts = line.split('\t')
            old_path = parts[1]
            new_path = parts[2]
            old_name = os.path.basename(old_path)
            new_name = os.path.basename(new_path)
            rename_map[old_name] = new_name
    return rename_map

def main():
    rename_map = get_rename_map()
    print(f"Loaded {len(rename_map)} rename mappings")

    total_replacements = 0
    fixed_files = 0

    for filename in sorted(os.listdir(POSTS_DIR)):
        if not filename.endswith('.md'):
            continue
        
        filepath = os.path.join(POSTS_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        new_content = content
        file_changed = False

        # Replace old filename refs in the entire file content
        # Match ref paths like "posts/old-name.md" (with or without quotes)
        for old_name, new_name in rename_map.items():
            # Skip self-reference (file referencing its own old name)
            # Only replace if the reference is to a different file
            if new_name == filename:
                continue

            # Replace in {{< ref "posts/old-name.md" >}} shortcodes
            pattern1 = f'{{{{< ref "posts/{old_name}" >}}}}'
            replacement1 = f'{{{{< ref "posts/{new_name}" >}}}}'
            if pattern1 in new_content:
                new_content = new_content.replace(pattern1, replacement1)
                file_changed = True

            # Replace in ref: posts/old-name.md
            pattern2 = f'ref: posts/{old_name}'
            replacement2 = f'ref: posts/{new_name}'
            if pattern2 in new_content:
                new_content = new_content.replace(pattern2, replacement2)
                file_changed = True

        if file_changed:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            fixed_files += 1
            # Count changes
            changes = 0
            for old_name in rename_map:
                for pattern in [
                    f'{{{{< ref "posts/{old_name}" >}}}}',
                    f'ref: posts/{old_name}'
                ]:
                    if pattern in content and pattern not in new_content:
                        changes += 1
            total_replacements += changes
            print(f"  FIXED {filename} ({changes} replacements)")

    print(f"\nFixed {fixed_files} files with {total_replacements} total replacements")

if __name__ == "__main__":
    main()
