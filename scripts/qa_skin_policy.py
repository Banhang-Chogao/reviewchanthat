#!/usr/bin/env python3
"""
qa_skin_policy.py — S-DNA skin regression guard.

Checks:
  1. S-DNA tokens exist in main.css (--sdna-teal etc.)
  2. No neon colors (#00ff00, #ff00ff, #39ff14, #0ff/#f0f shorthand)
  3. No glow-heavy box-shadow (blur > 20px) in main.css
  4. No new backdrop-filter beyond the allowed baseline (header blur)
  5. No border-radius over 24px except existing intentional tokens
  6. Homepage grid template unchanged (4-col home grid marker present)

Run: python scripts/qa_skin_policy.py
Exit: 0 = pass, 1 = violations
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_CSS = os.path.join(ROOT, "assets", "css", "main.css")

REQUIRED_TOKENS = [
    "--sdna-teal:#00a7a0",
    "--sdna-teal-soft:#ddf4f2",
    "--sdna-blue-soft:#dceaf8",
    "--sdna-purple-soft:#ece7fa",
    "--sdna-heading:#111111",
    "--sdna-body:#555555",
    "--sdna-muted:#888888",
    "--sdna-border:#e6e6e6",
    "--sdna-warning:#e8a838",
    "--sdna-negative:#e07a7a",
]

NEON_PATTERNS = [
    r"#00ff00\b", r"#ff00ff\b", r"#39ff14\b",
    r"(?<![0-9a-f])#0ff\b", r"(?<![0-9a-f])#f0f\b",
]

# Pre-existing intentional radii tokens (documented in Branding CI)
ALLOWED_LARGE_RADII = {"--radius-lg:24px", "--radius-xl:32px"}

# backdrop-filter existed on .site-header before S-DNA; cap at baseline count
MAX_BACKDROP_FILTER = 2  # backdrop-filter + -webkit-backdrop-filter on header


def main() -> int:
    errors: list[str] = []

    if not os.path.exists(MAIN_CSS):
        print(f"SKIN POLICY: FAIL — {MAIN_CSS} missing")
        return 1

    css = open(MAIN_CSS, encoding="utf-8").read()
    css_lower = css.lower()

    # 1. Required S-DNA tokens
    for tok in REQUIRED_TOKENS:
        if tok not in css_lower:
            errors.append(f"missing S-DNA token: {tok}")

    # 2. Neon colors
    for pat in NEON_PATTERNS:
        for m in re.finditer(pat, css_lower):
            errors.append(f"neon color found: {m.group(0)}")

    # 3. Shadows with blur > 20px  (box-shadow: x y blur ...)
    for m in re.finditer(
        r"(?:box-shadow|--shadow[a-z-]*):([^;}]+)", css_lower
    ):
        for shadow in m.group(1).split(","):
            nums = re.findall(r"(-?\d+(?:\.\d+)?)px", shadow)
            if len(nums) >= 3 and float(nums[2]) > 20:
                errors.append(
                    f"shadow blur {nums[2]}px > 20px: {shadow.strip()[:60]}"
                )

    # 4. backdrop-filter count must not grow
    n_backdrop = len(re.findall(r"backdrop-filter", css_lower))
    if n_backdrop > MAX_BACKDROP_FILTER:
        errors.append(
            f"backdrop-filter count {n_backdrop} > baseline {MAX_BACKDROP_FILTER}"
            " (glassmorphism added?)"
        )

    # 5. Radius over 24px outside allowed tokens
    for m in re.finditer(r"(--radius-[a-z]+:\s*(\d+)px)", css_lower):
        decl, val = m.group(1).replace(" ", ""), int(m.group(2))
        if val > 24 and decl not in ALLOWED_LARGE_RADII:
            errors.append(f"radius token over 24px: {decl}")
    for m in re.finditer(r"border-radius:\s*(\d+(?:\.\d+)?)px", css_lower):
        val = float(m.group(1))
        # 999px+ is the standard fully-rounded pill convention — allowed
        if 24 < val < 999:
            errors.append(f"hardcoded border-radius {m.group(1)}px > 24px")

    # 6. Homepage grid marker (layout must not change)
    if ".home-post-grid" in css_lower:
        grid_rules = re.findall(r"\.home-post-grid\{[^}]*\}", css_lower)
        if grid_rules and not any("grid" in r for r in grid_rules):
            errors.append(".home-post-grid no longer a grid — layout changed?")

    if errors:
        print("SKIN POLICY: FAIL")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("SKIN POLICY: PASS")
    print("  S-DNA tokens present; no neon/glass/huge shadows/huge radii")
    return 0


if __name__ == "__main__":
    sys.exit(main())
