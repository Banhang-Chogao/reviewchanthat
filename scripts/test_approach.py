#!/usr/bin/env python3
"""Test the approach on a few sample files before running full script."""

import sys
sys.path.insert(0, '/Users/duynguyen/Desktop/reviewchanthat/scripts')

from add_tom_tat_nhanh import *
from pathlib import Path

# Test 1: Parse table from bien-dep-o-jeju
print("=" * 60)
print("TEST 1: Parse table from bien-dep-o-jeju")
content1 = Path("/tmp/test_bien_dep.md").read_text(encoding='utf-8')
table_text = extract_table_from_section(content1, "## Tóm tắt nhanh")
print(f"Extracted table:\n{table_text}")
rows = parse_table_rows(table_text)
for label, value in rows:
    print(f"  {label}: {value}")

print("\n" + "=" * 60)
print("TEST 2: Parse table from caribbean-bay")
caribbean = Path("content/posts/caribbean-bay-yongin-cong-vien-nuoc-lon-gan-seoul-nen-di-ngay-nao.md").read_text(encoding='utf-8')
table_text2 = extract_table_from_section(caribbean, "## Tóm tắt nhanh")
print(f"Extracted table:\n{table_text2}")
rows2 = parse_table_rows(table_text2)
for label, value in rows2:
    print(f"  {label}: {value}")

print("\n" + "=" * 60)
print("TEST 3: Remove table section from bien-dep-o-jeju")
body = remove_table_section(content1, "## Tóm tắt nhanh")
print(f"Body starts with (first 200 chars): {body[:200]}")

print("\n" + "=" * 60)
print("TEST 4: Insert frontmatter into veritable-content")
content4 = Path("/tmp/test_veritable.md").read_text(encoding='utf-8')
test_data = [("Chủ đề", "Test label"), ("Mục đích", "Test value")]
result = insert_frontmatter(content4, test_data)
# Show the frontmatter section
parts = result.split('---\n', 2)
print(f"New frontmatter:\n{parts[1][:500]}")

print("\n" + "=" * 60)
print("TEST 5: WWDC26 da-qua special case")
content5 = Path("/tmp/test_wwdc26.md").read_text(encoding='utf-8')
table_text5 = extract_table_from_section(content5, "## Tóm tắt nhanh")
print(f"Extracted table from WWDC26:\n{table_text5[:200]}...")
rows5 = parse_table_rows(table_text5)
print(f"Parsed rows: {rows5}")
