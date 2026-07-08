#!/usr/bin/env python3
"""
Remove duplicate top-level keys from Hugo front matter.
Specifically removes duplicate attribution: blocks that were
introduced during the 56513c3 merge.
"""
import os
import re

POSTS_DIR = "content/posts"

# Keys that can appear at most once in front matter
SINGLETON_KEYS = [
    "attribution", "author", "avatar", "categories", "date",
    "description", "draft", "title", "tags", "image", "thumbnail",
    "image_source", "image_source_url", "image_license",
    "image_commercial_use", "image_owner",
]

def remove_duplicate_key(fm_text, key):
    """Remove all but the first occurrence of a top-level key."""
    # Find all occurrences of the key at the start of a line (top-level only)
    lines = fm_text.split('\n')
    new_lines = []
    found_first = False
    skip_until = -1  # line index to skip until
    
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if this is a top-level key
        m = re.match(rf'^({re.escape(key)})\s*:', line)
        if m:
            if not found_first:
                found_first = True
                new_lines.append(line)
            else:
                # Skip this key and all its content (indented lines)
                i += 1
                while i < len(lines) and (lines[i].startswith(' ') or lines[i].startswith('\t') or lines[i] == ''):
                    i += 1
                continue
        else:
            if found_first:
                pass  # keep all lines after first attribution
            new_lines.append(line)
        i += 1
    
    return '\n'.join(new_lines)

def main():
    fixed = 0
    for filename in sorted(os.listdir(POSTS_DIR)):
        if not filename.endswith('.md'):
            continue
        
        filepath = os.path.join(POSTS_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract front matter
        fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not fm_match:
            continue
        
        fm_text = fm_match.group(1)
        new_fm = fm_text
        
        changed = False
        for key in SINGLETON_KEYS:
            # Count occurrences of this top-level key
            occurrences = re.findall(rf'^{re.escape(key)}\s*:', new_fm, re.MULTILINE)
            if len(occurrences) > 1:
                new_fm = remove_duplicate_key(new_fm, key)
                changed = True
                count = len(occurrences) - len(re.findall(rf'^{re.escape(key)}\s*:', new_fm, re.MULTILINE))
                print(f"  {filename}: removed {count} duplicate '{key}'")
        
        if changed:
            new_content = f"---\n{new_fm}\n---\n" + content.split('---\n', 2)[2] if '---\n' in content[3:] else content
            # Proper replacement
            new_content = content.replace(fm_text, new_fm, 1)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            fixed += 1
    
    if fixed:
        print(f"\nFixed {fixed} files")

if __name__ == "__main__":
    main()
