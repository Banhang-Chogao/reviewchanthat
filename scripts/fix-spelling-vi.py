#!/usr/bin/env python3
"""
Vietnamese Spelling Auto-fixer for blog posts.
Automatically fixes common Vietnamese misspellings.
"""

import os
import re
from pathlib import Path
from typing import List, Dict

# Common Vietnamese spelling mistakes: {wrong_pattern: correct}
SPELLING_FIXES = {
    # Quản lý (management) - most common mistake
    r'\bquận\s*lý\b': 'quản lý',

    # Tài sản (assets)
    r'\btái\s*sản\b': 'tài sản',

    # Thị trường (market)
    r'\bthị\s*truờng\b': 'thị trường',

    # Lợi suất (return)
    r'\blợi\s*suất\b': 'lợi suất',

    # Chiết khấu (discount)
    r'\bchiết\s*khấu\b': 'chiết khấu',

    # Rủi ro (risk)
    r'\brủi\s*ro\b': 'rủi ro',

    # Danh mục (portfolio)
    r'\bdanh\s*mục\b': 'danh mục',

    # Phương sai (variance)
    r'\bphương\s*sai\b': 'phương sai',

    # Hiệp phương sai (covariance)
    r'\bhiệp\s*phương\s*sai\b': 'hiệp phương sai',

    # Công ty (company)
    r'\bcông\s*ty\b': 'công ty',

    # Dòng tiền (cash flow)
    r'\bdòng\s*tiền\b': 'dòng tiền',

    # Giá trị (value)
    r'\bgiá\s*trị\b': 'giá trị',

    # Định giá (valuation)
    r'\bđịnh\s*giá\b': 'định giá',

    # Phân tích (analysis)
    r'\bphân\s*tích\b': 'phân tích',

    # Chứng chỉ (certificate)
    r'\bchứng\s*chỉ\b': 'chứng chỉ',

    # Cấp bậc (level) - but be careful with "cấp"
    r'\bcấp\s*bậc\b': 'cấp bậc',

    # Độ nhạy (sensitivity)
    r'\bđộ\s*nhạy\b': 'độ nhạy',
}

class SpellingFixer:
    def __init__(self, root_dir: str, dry_run: bool = False):
        self.root_dir = Path(root_dir)
        self.dry_run = dry_run
        self.fixed_count = 0
        self.files_fixed = 0

    def find_markdown_files(self) -> List[Path]:
        """Find all markdown files in content/posts directory."""
        posts_dir = self.root_dir / 'content' / 'posts'
        if not posts_dir.exists():
            print(f"Warning: {posts_dir} not found")
            return []
        return sorted(posts_dir.glob('**/*.md'))

    def fix_file(self, filepath: Path) -> int:
        """Fix spelling in a single file. Returns number of fixes."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return 0

        original_content = content
        fixes = 0

        # Apply fixes
        for wrong_pattern, correct in SPELLING_FIXES.items():
            matches = list(re.finditer(wrong_pattern, content, re.IGNORECASE))
            if matches:
                content = re.sub(wrong_pattern, correct, content, flags=re.IGNORECASE)
                fixes += len(matches)

        # Write back if changes were made and not a dry run
        if fixes > 0 and content != original_content:
            if not self.dry_run:
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"✓ {filepath.name}: {fixes} fix(es)")
                except Exception as e:
                    print(f"Error writing {filepath}: {e}")
                    return 0
            else:
                print(f"[DRY RUN] {filepath.name}: {fixes} fix(es)")
            self.files_fixed += 1

        return fixes

    def run(self) -> None:
        """Run spelling fixes on all files."""
        markdown_files = self.find_markdown_files()

        if not markdown_files:
            print("No markdown files found!")
            return

        mode = "DRY RUN" if self.dry_run else "FIXING"
        print(f"🔧 {mode} spelling errors in {len(markdown_files)} files...\n")

        for filepath in markdown_files:
            fixes = self.fix_file(filepath)
            self.fixed_count += fixes

        print(f"\n{'=' * 50}")
        print(f"Files modified: {self.files_fixed}")
        print(f"Total fixes: {self.fixed_count}")
        print(f"{'=' * 50}\n")

        if self.dry_run:
            print("🔍 This was a dry run. Use --fix to actually modify files.")


def main():
    import sys

    # Check for --fix flag
    dry_run = '--fix' not in sys.argv
    root = Path(__file__).parent.parent

    fixer = SpellingFixer(str(root), dry_run=dry_run)
    fixer.run()


if __name__ == '__main__':
    main()
