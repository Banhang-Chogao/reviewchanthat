#!/usr/bin/env python3
"""
Vietnamese Spelling Checker for blog posts.
Checks for common Vietnamese misspellings and typos.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Common Vietnamese spelling mistakes: {wrong: correct}
SPELLING_MISTAKES = {
    # Quản lý (management)
    r'\bquận lý\b': 'quản lý',
    r'\bquận\s+lý\b': 'quản lý',

    # Tài sản (assets)
    r'\btái sản\b': 'tài sản',
    r'\btài\s+sản\b': 'tài sản',

    # Thị trường (market)
    r'\bthị\s+trường\b': 'thị trường',
    r'\bthị truờng\b': 'thị trường',

    # Lợi suất (return/profit)
    r'\blợi\s+suất\b': 'lợi suất',
    r'\blợi suất\b': 'lợi suất',

    # Chiết khấu (discount)
    r'\bchiết\s+khấu\b': 'chiết khấu',
    r'\bchiết khấu\b': 'chiết khấu',

    # Rủi ro (risk)
    r'\brủi\s+ro\b': 'rủi ro',
    r'\brủi ro\b': 'rủi ro',

    # Danh mục (portfolio)
    r'\bdanh\s+mục\b': 'danh mục',
    r'\bdanh mục\b': 'danh mục',

    # Phương sai (variance)
    r'\bphương\s+sai\b': 'phương sai',
    r'\bphương sai\b': 'phương sai',

    # Hiệp phương sai (covariance)
    r'\bhiệp\s+phương\s+sai\b': 'hiệp phương sai',

    # Công ty (company)
    r'\bcông\s+ty\b': 'công ty',
    r'\bcông ty\b': 'công ty',

    # Dòng tiền (cash flow)
    r'\bdòng\s+tiền\b': 'dòng tiền',
    r'\bdòng tiền\b': 'dòng tiền',

    # Giá trị (value)
    r'\bgiá\s+trị\b': 'giá trị',

    # Định giá (valuation)
    r'\bđịnh\s+giá\b': 'định giá',

    # Double spaces
    r'\s{2,}': ' ',
}

class SpellingChecker:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.errors: List[Dict] = []

    def find_markdown_files(self) -> List[Path]:
        """Find all markdown files in content/posts directory."""
        posts_dir = self.root_dir / 'content' / 'posts'
        if not posts_dir.exists():
            print(f"Warning: {posts_dir} not found")
            return []
        return sorted(posts_dir.glob('**/*.md'))

    def check_file(self, filepath: Path) -> List[Dict]:
        """Check a single file for spelling mistakes."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return []

        errors = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            for wrong_pattern, correct in SPELLING_MISTAKES.items():
                # Skip double space pattern for now (too noisy)
                if wrong_pattern == r'\s{2,}':
                    continue

                matches = re.finditer(wrong_pattern, line, re.IGNORECASE)
                for match in matches:
                    # Skip if this is in the correct word already
                    if match.group().lower() == correct.lower():
                        continue

                    errors.append({
                        'file': str(filepath.relative_to(self.root_dir)),
                        'line': line_num,
                        'column': match.start() + 1,
                        'wrong': match.group(),
                        'correct': correct,
                        'context': line.strip()[:100]
                    })

        return errors

    def run(self) -> bool:
        """Run spelling check on all files. Returns True if no errors found."""
        markdown_files = self.find_markdown_files()

        if not markdown_files:
            print("No markdown files found!")
            return True

        print(f"🔍 Checking {len(markdown_files)} files for spelling errors...\n")

        for filepath in markdown_files:
            file_errors = self.check_file(filepath)
            self.errors.extend(file_errors)

        # Group errors by file
        errors_by_file = {}
        for error in self.errors:
            file = error['file']
            if file not in errors_by_file:
                errors_by_file[file] = []
            errors_by_file[file].append(error)

        # Print results
        if errors_by_file:
            print(f"❌ Found {len(self.errors)} spelling error(s):\n")
            for file in sorted(errors_by_file.keys()):
                print(f"📄 {file}")
                for error in errors_by_file[file]:
                    print(f"   Line {error['line']:4d}, Col {error['column']:3d}: "
                          f"'{error['wrong']}' → '{error['correct']}'")
                    print(f"   Context: {error['context']}")
                print()
            return False
        else:
            print("✅ No spelling errors found!\n")
            return True


def main():
    root = Path(__file__).parent.parent
    checker = SpellingChecker(str(root))
    success = checker.run()

    # Exit with error code if errors found
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
