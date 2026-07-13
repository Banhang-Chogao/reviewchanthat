#!/usr/bin/env python3
"""
seo9_audit.py — Scan + auto-fix for Google AdSense, Search Console, and GA4 compliance.

Usage:
  python3 scripts/seo9_audit.py          # scan only
  python3 scripts/seo9_audit.py --fix     # scan + auto-fix

Exit code: 0 if no blocking issues remain, 1 otherwise.
"""

import argparse, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
LAYOUTS = ROOT / "layouts"
CONTENT = ROOT / "content"
DATA = ROOT / "data"
CI = ROOT / ".github" / "workflows"

GSC_VERIFY_FILE_PATTERN = re.compile(r"^google[0-9a-f]{16,}\.html$")

issues = []
fixes_applied = []


def report(severity: str, check: str, message: str):
    issues.append({"severity": severity, "check": check, "message": message})


# ─── Google Search Console ─────────────────────────────────────────────

def check_gsc():
    # 1. GSC verification file in static/
    gsc_files = [f for f in STATIC.iterdir() if GSC_VERIFY_FILE_PATTERN.match(f.name)]
    if gsc_files:
        report("OK", "GSC_VERIFY_FILE", f"Verification file found: {gsc_files[0].name}")
    else:
        report("ERROR", "GSC_VERIFY_FILE", "No Google Search Console verification file in static/")


    # 2. google-site-verification meta tag in seo.html
    seo_path = LAYOUTS / "partials" / "seo.html"
    if seo_path.exists():
        content = seo_path.read_text(encoding="utf-8")
        if 'google-site-verification' in content:
            report("OK", "GSC_META_TAG", "google-site-verification meta tag found in seo.html")
        elif gsc_files:
            report("WARN", "GSC_META_TAG",
                   "Missing google-site-verification meta tag in seo.html "
                   "(file verification exists, meta tag is recommended backup)")
        else:
            report("ERROR", "GSC_META_TAG", "No google-site-verification meta tag in seo.html")
    else:
        report("ERROR", "GSC_META_TAG", "layouts/partials/seo.html not found")


    # 3. robots.txt conflict
    static_robots = STATIC / "robots.txt"
    layout_robots = LAYOUTS / "robots.txt"
    has_static_robots = static_robots.exists()
    has_layout_robots = layout_robots.exists()
    if has_static_robots and has_layout_robots:
        report("WARN", "ROBOTS_CONFLICT",
               "Both static/robots.txt AND layouts/robots.txt exist — conflict; "
               "Hugo template takes precedence with enableRobotsTXT=true")
    elif has_layout_robots:
        report("OK", "ROBOTS_CONFLICT", "layouts/robots.txt (Hugo template) is the single source")
    elif has_static_robots:
        report("OK", "ROBOTS_CONFLICT", "static/robots.txt is the single source")
    else:
        report("ERROR", "ROBOTS_CONFLICT", "No robots.txt found")


    # 4. Sitemap in robots.txt
    if has_layout_robots:
        content = layout_robots.read_text(encoding="utf-8")
    elif has_static_robots:
        content = static_robots.read_text(encoding="utf-8")
    else:
        content = ""
    if "Sitemap:" in content:
        report("OK", "SITEMAP_IN_ROBOTS", "Sitemap URL found in robots.txt")
    else:
        report("WARN", "SITEMAP_IN_ROBOTS", "No Sitemap directive in robots.txt")


    # 5. Hugo sitemap config
    hugo_toml = ROOT / "hugo.toml"
    if hugo_toml.exists():
        toml_content = hugo_toml.read_text(encoding="utf-8")
        if "[sitemap]" in toml_content:
            report("OK", "HUGO_SITEMAP", "Hugo sitemap configuration found")
        else:
            report("WARN", "HUGO_SITEMAP", "No [sitemap] section in hugo.toml")


# ─── Google Analytics 4 ────────────────────────────────────────────────

def check_ga4():
    # 1. GA4 code in baseof.html
    baseof = LAYOUTS / "_default" / "baseof.html"
    if baseof.exists():
        content = baseof.read_text(encoding="utf-8")
        if "gtag/js" in content and "GA_MEASUREMENT_ID" in content:
            report("OK", "GA4_CODE", "GA4 gtag.js snippet found in baseof.html (env-driven)")
        elif "gtag/js" in content:
            report("OK", "GA4_CODE", "GA4 gtag.js found (but may use hardcoded ID)")
        else:
            report("ERROR", "GA4_CODE", "No GA4 gtag.js code in baseof.html")
    else:
        report("ERROR", "GA4_CODE", "layouts/_default/baseof.html not found")


    # 2. GA4 env var in CI/CD
    for yml in CI.glob("*.yml"):
        content = yml.read_text(encoding="utf-8")
        if "GA_MEASUREMENT_ID" in content:
            report("OK", "GA4_CI", f"GA_MEASUREMENT_ID configured in {yml.name}")
            break
    else:
        report("WARN", "GA4_CI", "GA_MEASUREMENT_ID not found in any CI workflow")


    # 3. GA4 security policy in hugo.toml
    hugo_toml = ROOT / "hugo.toml"
    if hugo_toml.exists():
        content = hugo_toml.read_text(encoding="utf-8")
        if "GA_MEASUREMENT_ID" in content and "getenv" in content:
            report("OK", "GA4_SECURITY", "GA_MEASUREMENT_ID allowed via security.funcs.getenv")
        else:
            report("WARN", "GA4_SECURITY", "GA_MEASUREMENT_ID may not be allowed by Hugo security policy")


    # 4. GA4 footer data
    ga4_data = DATA / "ga4_footer.json"
    if ga4_data.exists():
        import json
        try:
            d = json.loads(ga4_data.read_text(encoding="utf-8"))
            if d.get("status") == "ok":
                report("OK", "GA4_FOOTER_DATA",
                       f"GA4 footer data OK — Organic: {d.get('organic_search_users', '?')}, "
                       f"Total: {d.get('total_users', '?')} ({d.get('range_label', '')})")
            else:
                report("WARN", "GA4_FOOTER_DATA",
                       f"GA4 footer data status: {d.get('status')}")
        except (json.JSONDecodeError, KeyError) as e:
            report("WARN", "GA4_FOOTER_DATA", f"GA4 footer data parse error: {e}")
    else:
        report("WARN", "GA4_FOOTER_DATA", "No data/ga4_footer.json — stats box disabled")


# ─── Google AdSense ────────────────────────────────────────────────────

def check_adsense():
    # 1. ads.txt in static/
    ads_txt = STATIC / "ads.txt"
    if ads_txt.exists():
        content = ads_txt.read_text(encoding="utf-8").strip()
        if content and not content.startswith("#"):
            report("OK", "ADSENSE_ADS_TXT",
                   f"ads.txt exists ({len(content)} chars)")
        else:
            report("WARN", "ADSENSE_ADS_TXT", "ads.txt exists but appears empty or is all comments")
    else:
        report("ERROR", "ADSENSE_ADS_TXT",
               "Missing static/ads.txt — required by Google AdSense to verify inventory")


    # 2. AdSense JavaScript code in templates
    adsense_patterns = ["adsbygoogle", "adsense", "data-ad-client", "data-ad-slot", "ca-pub-"]
    found_adsense = False
    for pattern in adsense_patterns:
        for html_file in LAYOUTS.rglob("*.html"):
            if pattern in html_file.read_text(encoding="utf-8", errors="replace"):
                found_adsense = True
                break
        if found_adsense:
            break
    if found_adsense:
        report("OK", "ADSENSE_CODE", "AdSense JavaScript code found in templates")
    else:
        report("WARN", "ADSENSE_CODE",
               "No AdSense JavaScript found in templates — site cannot serve AdSense ads")


    # 3. Trip.com affiliate ads (existing monetization)
    trip_ad_count = 0
    for html_file in LAYOUTS.rglob("*.html"):
        if "trip.com" in html_file.read_text(encoding="utf-8", errors="replace"):
            trip_ad_count += 1
    if trip_ad_count > 0:
        report("OK", "AFFILIATE_ADS",
               f"Trip.com affiliate ads found ({trip_ad_count} placements) — alternate monetization active")


    # 4. AdBlock CTA
    adblock_cta = LAYOUTS / "partials" / "adblock-cta.html"
    if adblock_cta.exists():
        report("OK", "ADBLOCK_CTA", "Ad-block disable appeal found on homepage")


# ─── Auto-fix functions ───────────────────────────────────────────────

def fix_gsc_meta_tag():
    """Add google-site-verification meta tag to seo.html if missing."""
    seo_path = LAYOUTS / "partials" / "seo.html"
    if not seo_path.exists():
        return False

    content = seo_path.read_text(encoding="utf-8")
    if 'google-site-verification' in content:
        return True

    # Find the GSC verification file
    gsc_files = [f for f in STATIC.iterdir() if GSC_VERIFY_FILE_PATTERN.match(f.name)]
    if not gsc_files:
        report("ERROR", "FIX_GSC_META", "Cannot fix: no GSC verification file found")
        return False

    verify_id = gsc_files[0].name

    # Find the <title> line and insert meta tag after it
    # Or better: insert after <link rel="canonical">
    markers = [
        '<link rel="canonical"',
        '<link rel="sitemap"',
        '<meta name="robots"',
        '<title>',
    ]
    insert_pos = None
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if any(m in line for m in markers):
            insert_pos = i + 1
            break

    if insert_pos is None:
        insert_pos = 5  # fallback

    meta_tag = f'<meta name="google-site-verification" content="{verify_id}">'
    lines.insert(insert_pos, meta_tag)
    new_content = "\n".join(lines)
    seo_path.write_text(new_content, encoding="utf-8")
    fixes_applied.append(f"Added google-site-verification meta tag to layouts/partials/seo.html")
    return True


def fix_robots_conflict():
    """Remove static/robots.txt if layouts/robots.txt (Hugo template) exists."""
    static_robots = STATIC / "robots.txt"
    layout_robots = LAYOUTS / "robots.txt"
    if static_robots.exists() and layout_robots.exists():
        static_robots.unlink()
        fixes_applied.append("Removed static/robots.txt (conflict with layouts/robots.txt Hugo template)")
        return True
    elif static_robots.exists() and not layout_robots.exists():
        report("WARN", "FIX_ROBOTS",
               "static/robots.txt exists without layouts/robots.txt — no conflict to fix")
        return True
    return True


def fix_ads_txt():
    """Create placeholder ads.txt in static/ if missing."""
    ads_txt = STATIC / "ads.txt"
    if ads_txt.exists():
        return True

    content = (
        "# ads.txt — Google AdSense inventory verification\n"
        "# Replace the line below with your actual AdSense publisher ID.\n"
        "# Example:\n"
        "# google.com, pub-0000000000000000, DIRECT, f08c47fec0942fa0\n"
        "\n"
        "# To get your publisher ID, sign in to https://adsense.google.com\n"
        "# and go to Settings > Account > Account ID (ca-pub-XXXXXXXXXXXXXX).\n"
    )
    ads_txt.write_text(content, encoding="utf-8")
    fixes_applied.append("Created static/ads.txt placeholder — replace with actual AdSense publisher ID before going live")
    return True


# ─── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SEO9 audit: AdSense, GSC, GA4 compliance")
    parser.add_argument("--fix", action="store_true", help="Auto-fix detected issues")
    args = parser.parse_args()

    print("=" * 64)
    print("  SEO9 Audit — Google AdSense · Search Console · GA4")
    print("=" * 64)

    check_gsc()
    check_ga4()
    check_adsense()

    # Print report
    print(f"\n{'─── Report ───':^64}")
    severity_order = {"ERROR": 0, "WARN": 1, "OK": 2}
    sorted_issues = sorted(issues, key=lambda x: (severity_order.get(x["severity"], 99), x["check"]))

    for iss in sorted_issues:
        icon = {"OK": "✅", "WARN": "⚠️", "ERROR": "❌"}.get(iss["severity"], "❓")
        print(f"  {icon} [{iss['severity']:5s}] {iss['check']:20s}  {iss['message']}")

    errors = [i for i in issues if i["severity"] == "ERROR"]
    warnings = [i for i in issues if i["severity"] == "WARN"]
    print(f"\n  Summary: {len(errors)} errors, {len(warnings)} warnings, "
          f"{len([i for i in issues if i['severity']=='OK'])} OK")

    # Auto-fix
    if args.fix:
        print(f"\n{'─── Auto-fix ───':^64}")
        fix_gsc_meta_tag()
        fix_robots_conflict()
        fix_ads_txt()
        if fixes_applied:
            for f in fixes_applied:
                print(f"  🔧 {f}")
        else:
            print("  ✅ No fixes needed")
        print()

    # Refresh issues after fix for final count
    if args.fix:
        issues.clear()
        check_gsc()
        check_ga4()
        check_adsense()
        remaining_errors = [i for i in issues if i["severity"] == "ERROR"]
        remaining_warnings = [i for i in issues if i["severity"] == "WARN"]
        print(f"{'─── Post-fix status ───':^64}")
        for iss in issues:
            icon = {"OK": "✅", "WARN": "⚠️", "ERROR": "❌"}.get(iss["severity"], "❓")
            print(f"  {icon} [{iss['severity']:5s}] {iss['check']:20s}  {iss['message']}")
        print(f"\n  Remaining: {len(remaining_errors)} errors, {len(remaining_warnings)} warnings")

        if remaining_errors:
            print("\n  ❌ Manual action required for remaining errors. See above.")
            return 1
        elif remaining_warnings:
            print("\n  ⚠️  Warnings remain (non-blocking). Review recommended.")
            return 0
        else:
            print("\n  ✅ All clear!")
            return 0

    if errors:
        print("\n  ❌ Run with --fix to auto-resolve fixable issues.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
