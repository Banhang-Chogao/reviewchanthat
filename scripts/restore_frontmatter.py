#!/usr/bin/env python3
"""
Restore missing front matter fields (title, image, thumbnail, etc.)
from commit f99bbfd to the 22 posts that lost them in merge 56513c3.
"""
import os
import subprocess
import re

POSTS_DIR = "content/posts"

# Fields to restore, in order they should appear
FIELDS_TO_RESTORE = [
    "title", "description", "author", "avatar", "date", "draft",
    "categories", "tags",
    "image", "thumbnail", "image_source", "image_source_url",
    "image_license", "image_commercial_use", "image_owner",
]

def get_good_frontmatter(filename):
    """Extract front matter from commit f99bbfd for a given file."""
    result = subprocess.run(
        ["git", "show", f"f99bbfd:content/posts/{filename}"],
        capture_output=True, text=True, cwd="."
    )
    if result.returncode != 0:
        return None
    
    content = result.stdout
    # Extract front matter between --- markers
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None
    return match.group(1)

def parse_frontmatter_lines(fm_text):
    """Parse front matter text into a dict of key -> (indent_level, value_lines)."""
    result = {}
    current_key = None
    current_indent = 0
    current_lines = []
    
    for line in fm_text.split('\n'):
        # Check for top-level key
        top_match = re.match(r'^(\w[\w_-]*)\s*:', line)
        if top_match and (len(line) == len(top_match.group(0)) or line[len(top_match.group(0))] in ' \t'):
            # Save previous
            if current_key:
                result[current_key] = (current_indent, current_lines)
            current_key = top_match.group(1)
            current_indent = 0
            current_lines = [line]
            continue
        
        # Check for nested key (list item or dict)
        nested_match = re.match(r'^(\s+)(\w[\w_-]*)\s*:', line)
        if nested_match and current_key:
            indent = len(nested_match.group(1))
            if indent > current_indent:
                # Still within the same top-level object
                current_lines.append(line)
                continue
        
        if current_key:
            current_lines.append(line)
    
    if current_key:
        result[current_key] = (current_indent, current_lines)
    
    return result

def get_field_value(fm_text, field_name):
    """Extract the value of a specific field from front matter text."""
    # Handle multi-line quoted strings
    lines = fm_text.split('\n')
    in_field = False
    value_lines = []
    for i, line in enumerate(lines):
        if re.match(rf'^{re.escape(field_name)}\s*:', line):
            in_field = True
            value_lines.append(line)
        elif in_field:
            if re.match(r'^\w', line) and ':' in line:
                break
            if line.strip().startswith('#'):
                break
            if line.strip() == '':
                break
            value_lines.append(line)
    return '\n'.join(value_lines) if value_lines else None

def get_current_frontmatter_and_body(filepath):
    """Split current file into front matter and body."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    match = re.match(r'^---\s*\n(.*?)\n---\n?(.*)', content, re.DOTALL)
    if match:
        return match.group(1), match.group(2)
    return None, content

def main():
    # Identify broken posts (missing title)
    broken = []
    for f in sorted(os.listdir(POSTS_DIR)):
        if not f.endswith('.md'):
            continue
        filepath = os.path.join(POSTS_DIR, f)
        fm, body = get_current_frontmatter_and_body(filepath)
        if fm is None:
            print(f"SKIP {f}: no front matter")
            continue
        if not re.search(r'^title\s*:', fm, re.MULTILINE):
            broken.append(f)
    
    print(f"Found {len(broken)} broken posts\n")
    
    for filename in broken:
        filepath = os.path.join(POSTS_DIR, filename)
        good_fm = get_good_frontmatter(filename)
        if good_fm is None:
            print(f"SKIP {filename}: not found in f99bbfd")
            continue
        
        current_fm, body = get_current_frontmatter_and_body(filepath)
        
        # Extract missing fields from good front matter
        # Skip fields that already exist in current front matter
        missing_block = ""
        for field in FIELDS_TO_RESTORE:
            if re.search(rf'^{re.escape(field)}\s*:', current_fm, re.MULTILINE):
                continue
            val = get_field_value(good_fm, field)
            if val:
                missing_block += val + "\n"
        
        # Insert missing fields before `slug:` line
        # Also clean up empty `aliases:` line
        new_fm = current_fm
        
        # Fix empty aliases: (replace "aliases:\n---" with "---")
        if re.search(r'^aliases:\s*\n---', new_fm, re.MULTILINE):
            new_fm = re.sub(r'\naliases:\s*\n?', '\n', new_fm)
        elif re.search(r'^aliases:\s*$', new_fm, re.MULTILINE):
            new_fm = re.sub(r'^aliases:\s*$', '', new_fm, flags=re.MULTILINE)
        # Also fix "\naliases:\n\n" patterns
        new_fm = re.sub(r'\n+aliases:\s*\n+', '\n', new_fm)
        new_fm = re.sub(r'^aliases:\s*\n+', '', new_fm)
        
        # Insert missing fields before `slug:`
        slug_pos = new_fm.find('\nslug:')
        if slug_pos == -1:
            # Maybe starts with slug
            if new_fm.startswith('slug:'):
                slug_pos = -1
            else:
                print(f"  WARN {filename}: no slug line found")
                slug_pos = len(new_fm)
        
        if slug_pos >= 0:
            new_fm = new_fm[:slug_pos] + '\n' + missing_block.rstrip('\n') + new_fm[slug_pos:]
        else:
            new_fm = new_fm + '\n' + missing_block.rstrip('\n')
        
        # Remove duplicate blank lines
        new_fm = re.sub(r'\n{3,}', '\n\n', new_fm)
        
        # Write back
        new_content = f"---\n{new_fm.strip()}\n---\n{body}"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"  FIXED {filename}")
    
    print("\nDone. Restored missing front matter to broken posts.")

if __name__ == "__main__":
    main()
