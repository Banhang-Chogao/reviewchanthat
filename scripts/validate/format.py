#!/usr/bin/env python3
"""
Format Validator for Hugo Posts

Validates:
1. Frontmatter format (TOML only, no YAML+TOML dual)
2. Alphabetical ordering of keys
3. Required fields presence
4. Date format (ISO 8601 with timezone)
"""

import sys
import re
from typing import List, Tuple, Dict


class FormatValidator:
    """Validate Hugo post format."""

    REQUIRED_FIELDS = {
        'title', 'description', 'date'
    }

    def __init__(self, filename: str):
        self.filename = filename
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def read_file(self) -> List[str]:
        """Read file lines."""
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                return f.readlines()
        except FileNotFoundError:
            self.errors.append(f"File not found: {self.filename}")
            return []

    def extract_frontmatter(self, lines: List[str]) -> Tuple[List[str], int]:
        """
        Extract frontmatter lines.

        Returns:
            (frontmatter_lines, end_line_number)
        """
        if not lines or lines[0].strip() != '+++':
            self.errors.append("Missing TOML frontmatter delimiter (+++) at start")
            return [], 0

        frontmatter = []
        for i in range(1, len(lines)):
            line = lines[i].strip()
            if line == '+++':
                return lines[1:i], i + 1

        self.errors.append("Unclosed TOML frontmatter (missing closing +++)")
        return [], 0

    def check_no_yaml(self, lines: List[str]) -> bool:
        """Check no YAML frontmatter (---) present."""
        for i, line in enumerate(lines[:20]):  # Check first 20 lines
            if line.strip().startswith('---'):
                self.errors.append(
                    f"Line {i+1}: YAML frontmatter (---) found. "
                    "Use TOML only (+++), no dual YAML+TOML."
                )
                return False
        return True

    def check_alphabetical_order(self, frontmatter: List[str]) -> bool:
        """Check keys in alphabetical order."""
        keys_found = []

        for i, line in enumerate(frontmatter, start=2):  # Start from line 2 (after +++)
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Parse key = value
            match = re.match(r'^(\w+)\s*=', line)
            if not match:
                # Could be nested table or array, skip for now
                continue

            key = match.group(1)
            keys_found.append((key, i))

        # Check alphabetical order
        for i in range(1, len(keys_found)):
            prev_key, prev_line = keys_found[i-1]
            curr_key, curr_line = keys_found[i]

            if prev_key > curr_key:
                self.errors.append(
                    f"Line {curr_line}: Keys not in alphabetical order. "
                    f"'{curr_key}' should come before '{prev_key}'"
                )
                return False

        return True

    def check_required_fields(self, frontmatter: List[str]) -> bool:
        """Check required fields present."""
        found_fields = set()

        for line in frontmatter:
            match = re.match(r'^(\w+)\s*=', line.strip())
            if match:
                found_fields.add(match.group(1))

        missing = self.REQUIRED_FIELDS - found_fields
        if missing:
            self.errors.append(
                f"Missing required fields: {', '.join(sorted(missing))}"
            )
            return False

        return True

    def check_date_format(self, frontmatter: List[str]) -> bool:
        """Check date is ISO 8601 with timezone."""
        for i, line in enumerate(frontmatter, start=2):
            if line.strip().startswith('date'):
                # Expected: date = 2026-07-11T12:00:00+07:00
                match = re.search(
                    r'date\s*=\s*["\']?(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2})["\']?',
                    line
                )
                if not match:
                    self.errors.append(
                        f"Line {i}: Date must be ISO 8601 format with timezone. "
                        "Example: 2026-07-11T12:00:00+07:00"
                    )
                    return False
                break

        return True

    def validate(self) -> bool:
        """Run all validations."""
        lines = self.read_file()
        if not lines:
            return False

        # Check no YAML
        self.check_no_yaml(lines)

        # Extract frontmatter
        frontmatter, _ = self.extract_frontmatter(lines)
        if not frontmatter:
            return False

        # Check required fields
        self.check_required_fields(frontmatter)

        # Check date format
        self.check_date_format(frontmatter)

        # Check alphabetical order
        self.check_alphabetical_order(frontmatter)

        return len(self.errors) == 0

    def report(self):
        """Print validation report."""
        if self.errors:
            print(f"❌ {self.filename}")
            for error in self.errors:
                print(f"  ERROR: {error}")
            return False

        if self.warnings:
            print(f"⚠️  {self.filename}")
            for warning in self.warnings:
                print(f"  WARNING: {warning}")
            return True

        print(f"✅ {self.filename}")
        return True


def main(filename: str):
    """Validate single file."""
    validator = FormatValidator(filename)
    is_valid = validator.validate()
    validator.report()

    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate/format.py <filename>")
        sys.exit(1)

    main(sys.argv[1])
