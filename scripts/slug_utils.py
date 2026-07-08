#!/usr/bin/env python3
"""Shared Vietnamese slug utilities for Review Chân Thật.

Rule: title -> deterministic ASCII slug.
- lowercase
- strip Vietnamese diacritics (NFC decompose -> drop combining marks)
- 'đ' -> 'd'
- '&' -> 'va'
- remove all other punctuation / special chars
- whitespace and runs of non-alphanumerics collapse to single '-'
- trim leading/trailing '-'
- keep only [a-z0-9-]
"""

import re
import unicodedata


def slugify_vi(title: str) -> str:
    if not title:
        return ""
    s = title.lower().strip()
    # decompose accented chars
    s = unicodedata.normalize("NFKD", s)
    # drop combining marks (diacritics)
    s = "".join(c for c in s if not unicodedata.combining(c))
    # 'đ' becomes 'd' (đ is not a combining diacritic)
    s = s.replace("đ", "d")
    # '&' -> 'va'
    s = s.replace("&", "va")
    # remove punctuation / special characters (keep alnum, spaces, hyphens)
    s = re.sub(r"[^a-z0-9\s-]", " ", s)
    # collapse whitespace/hyphen runs into single hyphen
    s = re.sub(r"[\s-]+", "-", s)
    # trim
    s = s.strip("-")
    return s


if __name__ == "__main__":
    import sys

    tests = [
        "Top 20 hoạt động khi du lịch Hàn Quốc 2026: chơi gì ở Seoul, Busan, Jeju và gần Seoul?",
        "Địa điểm quay phim Hàn Quốc ở Seoul: đi theo dấu K-drama mà không bị quá touristic",
        "Lotte World Adventure Seoul: có hợp đi cùng trẻ em và gia đình không?",
    ]
    if len(sys.argv) > 1:
        print(slugify_vi(" ".join(sys.argv[1:])))
    else:
        for t in tests:
            print(f"{t}\n  -> {slugify_vi(t)}\n")
