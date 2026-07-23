#!/usr/bin/env python3
"""Bounded SEO remediation for Review Chân Thật.

This tool deliberately keeps article URLs, visible H1 titles, dates and images
unchanged.  It is designed for a one-off repair as well as repeatable audits:

* ``links`` rebuilds ``data/internal-links.json`` from semantic evidence and
  adds two contextual, in-body links only to posts that genuinely have none.
* ``metadata`` adds or refines a separate ``seo_title`` and shortens only
  descriptions outside the 50–160 character contract.
* ``hubs`` marks existing, substantive posts as pillars.  The link graph then
  makes hub/satellite recommendations bidirectional without Markdown end
  blocks.
* ``report`` prints the same measurements used by Content Direction.

No command changes article dates or ``lastmod``.  A meaningful editorial or
fact update must own those fields separately.
"""

from __future__ import annotations

import argparse
import json
import re
import tomllib
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "content" / "posts"
GRAPH_PATH = ROOT / "data" / "internal-links.json"
REPORT_PATH = ROOT / "reports" / "seo-remediation-report.json"

TITLE_MIN, TITLE_MAX = 30, 60
DESCRIPTION_MIN, DESCRIPTION_MAX = 50, 160
MAX_GRAPH_LINKS = 8
BASE_GRAPH_LINKS = 6

# These are existing, long-form overview posts.  Keeping hubs in data rather
# than creating five near-duplicate articles avoids cannibalising their intent.
HUBS = {
    "du-lich": "top-20-hoat-dong-khi-du-lich-han-quoc-2026-choi-gi-o-seoul-busan-jeju-va-gan-seoul",
    "cong-nghe": "wwdc26-da-qua-nhan-dinh-sau-su-kien-ve-siri-ai-ios-27-va-nhung-gi-apple-chua-noi",
    "tai-chinh": "quan-ly-tai-chinh-ca-nhan-cho-nguoi-moi-di-lam-2026",
    "doi-song": "song-thong-minh-trong-thoi-dai-ai-cach-ai-dang-thay-doi-cuoc-song-hang-ngay",
    "review": "review-cong-nghe-nen-tin-benchmark-hay-trai-nghiem-that",
}

# Curated from the exact baseline violations.  The fallback remains useful for
# future audits, but these titles deserve editorial wording rather than an
# automated character-cut in the middle of a Vietnamese phrase.
TITLE_OVERRIDES = {
    "ai-model-wars-july-2026-gpt-5-6-vs-grok-4-5-vs-gemini-3-5-pro": "GPT-5.6 vs Grok 4.5 vs Gemini 3.5 Pro: so sánh AI",
    "ai-productivity-tools-2026-honest-review": "Best AI Productivity Tools in 2026",
    "ai-travel-planner-la-gi-cach-tao-lich-trinh-chuyen-nghiep": "AI Travel Planner: tạo lịch trình du lịch bằng AI",
    "am-thuc-nauy-tu-ca-hoi-den-truyen-thong-viking": "Ẩm thực Nauy: cá hồi, lutefisk và văn hóa Viking",
    "anjung-house-eleena-jamil-review": "Review Anjung House: kiến trúc bản địa Malaysia",
    "balo-cabin-40l-di-han-quoc": "Balo cabin 40L đi Hàn: chọn size và đồ cần mang",
    "bao-mat-wifi-cong-cong-nguy-co-cach-phong-tranh": "Bảo mật WiFi công cộng: cách phòng tránh rủi ro",
    "bao-ve-du-lieu-ca-nhan-tren-internet-huong-dan-toan-dien-2026": "Bảo vệ dữ liệu cá nhân trên Internet: hướng dẫn 2026",
    "best-wireless-earbuds-2026-top-picks-review": "Best Wireless Earbuds 2026: Top Picks for Every Budget",
    "cach-viet-visa-itinerary-chuyen-nghiep": "Cách viết visa itinerary chuyên nghiệp, đúng chuẩn",
    "cau-tren-bien-ngam-dien-gio-ca-mau": "Cầu trên biển Cà Mau: ngắm điện gió và kinh nghiệm đi",
    "christopher-nolan-tieu-su-va-su-nghiep": "Christopher Nolan: sự nghiệp từ indie đến Odyssey",
    "chuyen-tu-android-sang-iphone-2026": "Chuyển từ Android sang iPhone: cần chuẩn bị gì?",
    "coyote-vs-acme-2026-review": "Coyote vs. Acme (2026): review không spoil",
    "dau-tu-thong-minh-thoi-lai-suat-thap-2026": "Đầu tư thời lãi suất thấp 2026: chiến lược cho người Việt",
    "don-dep-dien-thoai-1-buoi-tap-trung": "Dọn dẹp điện thoại: lấy lại sự tập trung trong 1 buổi",
    "du-lich-da-lat-mua-hoa-dang-cho-2026": "Du lịch Đà Lạt mùa hoa 2026: lịch trình và chi phí",
    "even-realities-g2-smart-glasses-review": "Even Realities G2: review kính thông minh không camera",
    "hoang-toc-na-uy-hien-dai-chan-dung-than-quyen-duoi-thoi-vua-harald-v": "Hoàng tộc Na Uy: chân dung dưới thời Vua Harald V",
    "hoi-an-pho-co-di-san-the-gioi": "Hội An: kinh nghiệm khám phá phố cổ di sản",
    "khach-san-view-dep-gan-ha-noi-2026": "Khách sạn view đẹp gần Hà Nội: review và kinh nghiệm",
    "khach-san-view-dep-gan-tphcm-nghi-duong-2026": "Khách sạn view đẹp gần TP.HCM: review và kinh nghiệm",
    "khach-san-view-dep-hai-phong-cat-ba-2026": "Khách sạn view đẹp Hải Phòng, Cát Bà: review 2026",
    "kham-pha-mien-tay-song-nuoc-2026": "Khám phá miền Tây mùa nước nổi 2026: lịch trình dễ đi",
    "kindle-scribe-2-review-2026": "Kindle Scribe 2 Review: six months as a notebook",
    "kinh-nghiem-du-lich-nauy-tu-tuc-tu-oslo-den-bac-cuc": "Du lịch Nauy tự túc: Oslo, Bắc Cực và chi phí",
    "kinh-nghiem-du-lich-tet-2027": "Du lịch Tết Đinh Mùi 2027: lịch trình và đặt phòng",
    "kinh-te-Nauy-dau-mo-quy-dau-tu-va-mo-hinh-phuc-loi": "Kinh tế Nauy: dầu mỏ, quỹ đầu tư và phúc lợi",
    "mac-hay-windows-2026-dan-van-phong": "Mac hay Windows 2026: chi phí 3 năm cho dân văn phòng",
    "mau-lich-trinh-chau-au-nhieu-nuoc-ai": "Lịch trình châu Âu nhiều nước: mẫu 7–14 ngày bằng AI",
    "mau-lich-trinh-han-quoc-7-ngay-ai": "Lịch trình Hàn Quốc 7 ngày: mẫu chi tiết bằng AI",
    "mau-lich-trinh-nhat-ban-7-ngay-ai": "Lịch trình Nhật Bản 7 ngày: mẫu chi tiết bằng AI",
    "mau-lich-trinh-xin-visa-huong-dan-day-du": "Mẫu lịch trình xin visa: cách lập đúng chuẩn",
    "meal-prep-5-ngay-nguoi-ban-viet-nam": "Meal prep 5 ngày: thực đơn Việt cho người bận",
    "michelin-restaurants-ho-chi-minh-city-must-try": "Michelin restaurants in Ho Chi Minh City 2026",
    "moana-live-action-2026-review": "Moana live-action (2026): review không spoil",
    "msi-claw-8-ex-ai-plus-review": "MSI Claw 8 EX AI+: review máy chơi game cầm tay",
    "nhung-loi-thuong-gap-khi-chuan-bi-lich-trinh-xin-visa": "Lỗi visa itinerary thường gặp và cách tránh",
    "personal-finance-young-vietnamese-2026": "Personal finance 2026 cho người trẻ Việt Nam",
    "review-asus-zenbook-duo-2026-laptop-2-man-hinh": "Review ASUS Zenbook DUO 2026: laptop hai màn hình",
    "review-robot-hut-bui-lau-nha-2026-roborock-xiaomi-ecovacs": "Review robot hút bụi lau nhà: Roborock, Xiaomi, Ecovacs",
    "review-shopee-lazada-tiki-so-sanh-mua-sam-online-2026": "Shopee, Lazada, Tiki: app nào đáng mua 2026?",
    "review-super-8-2011-biet-doi-thieu-nien-va-bi-an": "Review Super 8 (2011): bí ẩn chuyến tàu năm 1979",
    "review-vpn-2026-nordvpn-surfshark-protonvpn-viet-nam": "Review VPN 2026: NordVPN, Surfshark hay ProtonVPN?",
    "routine-buoi-sang-45-phut-nguoi-di-lam": "Routine buổi sáng 45 phút thực tế cho người đi làm",
    "samsung-galaxy-s26-ultra-six-month-review": "Samsung Galaxy S26 Ultra: đánh giá sau 6 tháng",
    "schengen-visa-itinerary-cach-lap-lich-trinh-xin-visa-schengen": "Schengen visa itinerary: cách lập lịch trình chuẩn",
    "so-sanh-grabfood-shopeefood-baemin-trai-nghiem-giao-do-an-2026": "GrabFood, ShopeeFood, Baemin: app nào tốt hơn?",
    "so-sanh-ve-may-bay-tet-2027": "So sánh vé máy bay Tết 2027: hãng nào rẻ hơn?",
    "spider-man-brand-new-day-2026-review": "Spider-Man: Brand New Day (2026): review không spoil",
    "su-thi-odyssey-hanh-trinh-20-nam-tro-ve-nha": "Sử thi Odyssey: hành trình 20 năm trở về nhà",
    "supergirl-2026-review": "Supergirl (2026): review không spoil về DCU mới",
    "the-odyssey-2026-review": "The Odyssey (2026): review phim Christopher Nolan",
    "toi-uu-wifi-nha-pho-chung-cu-viet-nam": "Tối ưu WiFi nhà phố: đặt router và chọn mesh",
    "travel-budget-cach-lap-ngan-sach-du-lich-thong-minh": "Travel budget: lập ngân sách du lịch trước chuyến đi",
    "travel-checklist-danh-sach-chuan-bi-truoc-chuyen-di-quoc-te": "Travel checklist: chuẩn bị gì trước chuyến đi",
    "trending-topic-20260713": "AI Inflation 2026: vì sao laptop và điện thoại tăng giá",
    "trending-topic-20260714": "Gemini 3.5 Pro: giá, ngữ cảnh 2M và Deep Think",
    "trending-topic-20260715": "GPT-5.6 vs Grok 4.5 vs Muse Spark: so sánh AI",
    "visa-han-bi-tu-choi-ly-do-va-lan-2": "Visa Hàn bị từ chối: lý do và hồ sơ lần 2",
}

DESCRIPTION_OVERRIDES = {
    "schengen-visa-itinerary-cach-lap-lich-trinh-xin-visa-schengen": "Hướng dẫn lập Schengen visa itinerary đúng chuẩn lãnh sự: quy tắc nhập cảnh, số ngày lưu trú, trình tự nước đến và lỗi cần tránh.",
}

# The 36 baseline posts with no outbound link receive two links in the body.
# These editorial pairings were reviewed against title, category, tags, entity
# overlap and article intent; they take precedence over the general scorer.
CONTEXTUAL_TARGET_OVERRIDES = {
    "ai-productivity-tools-2026-honest-review": ["20-cong-cu-ai-giup-tiet-kiem-it-nhat-2-gio-moi-ngay", "song-thong-minh-trong-thoi-dai-ai-cach-ai-dang-thay-doi-cuoc-song-hang-ngay"],
    "anjung-house-eleena-jamil-review": ["thiet-ke-nordic-toida-gian-noi-that", "mo-hinh-phang-tiet-lo-tu-ikea-va-volvo"],
    "balo-cabin-40l-di-han-quoc": ["checklist-vali-di-han-mua-he-mac-gi-mang-gi-de-khong-kho-vi-nong-mua", "jet-lag-han-viet-ngu-du-48-gio-dau"],
    "bao-hiem-du-lich-quoc-te-khi-nao-can": ["mau-lich-trinh-xin-visa-huong-dan-day-du", "travel-budget-cach-lap-ngan-sach-du-lich-thong-minh"],
    "chi-phi-that-nuoi-iphone-3-nam": ["quan-ly-tai-chinh-ca-nhan-cho-nguoi-moi-di-lam-2026", "co-nen-mua-dien-thoai-moi-viet-nam-2026"],
    "chuyen-tu-android-sang-iphone-2026": ["don-iphone-nhu-the-nao-de-may-luon-muot-va-con-nhieu-bo-nho", "ios-27-co-nen-cap-nhat-ngay-khong"],
    "coyote-vs-acme-2026-review": ["review-paradise-2023-nguoi-giau-mua-thoi-gian-song", "review-super-8-2011-biet-doi-thieu-nien-va-bi-an"],
    "dau-tu-thong-minh-thoi-lai-suat-thap-2026": ["quan-ly-tai-chinh-ca-nhan-cho-nguoi-moi-di-lam-2026", "nen-mua-vang-gui-tiet-kiem-hay-dau-tu-chung-khoan-nam-2026"],
    "don-dep-dien-thoai-1-buoi-tap-trung": ["digital-detox-la-gi-cach-giam-phu-thuoc-dien-thoai-ma-khong-mat-ket-noi", "don-gmail-dung-cach-giam-hang-nghin-email-rac-chi-trong-mot-buoi-toi"],
    "github-actions-run-start-delays-july-9-2026-ci-cd-protection": ["ci-cd-root-cause-playbook-safe-vs-unsafe-autofix", "github-api-va-pages-rate-limit-cach-doc-va-giam-tai"],
    "hoi-an-pho-co-di-san-the-gioi": ["du-lich-da-nang-he-2026-lich-trinh-4-ngay-3-dem", "vietnam-travel-guide-2026"],
    "jet-lag-han-viet-ngu-du-48-gio-dau": ["balo-cabin-40l-di-han-quoc", "lich-trinh-seoul-3-ngay-mua-mua-cho-nguoi-di-lan-dau"],
    "kham-pha-mien-tay-song-nuoc-2026": ["bien-ba-dong-tra-vinh", "vietnam-travel-guide-2026"],
    "kindle-scribe-2-review-2026": ["ai-productivity-tools-2026-honest-review", "mac-hay-windows-2026-dan-van-phong"],
    "kinh-nghiem-cam-trai-cho-nguoi-moi-2026": ["trao-luu-green-camping-cam-trai-hoang-so", "du-lich-may-do-trai-nghiem-ban-dia"],
    "kinh-nghiem-du-lich-tet-2027": ["agoda-la-gi-co-uy-tin-an-toan-khong", "review-dat-ve-may-bay-tau-hoa-tet-2027-meo-san-ve-som-khong-bi-ho"],
    "mac-hay-windows-2026-dan-van-phong": ["macos-27-beta-co-nen-cai-khong", "macos-27-cho-van-phong-creator-lap-trinh-vien"],
    "mau-lich-trinh-xin-visa-huong-dan-day-du": ["cach-viet-visa-itinerary-chuyen-nghiep", "ai-travel-planner-la-gi-cach-tao-lich-trinh-chuyen-nghiep"],
    "meal-prep-5-ngay-nguoi-ban-viet-nam": ["routine-buoi-sang-45-phut-nguoi-di-lam", "don-dep-dien-thoai-1-buoi-tap-trung"],
    "moana-live-action-2026-review": ["coyote-vs-acme-2026-review", "review-super-8-2011-biet-doi-thieu-nien-va-bi-an"],
    "personal-finance-young-vietnamese-2026": ["quan-ly-tai-chinh-ca-nhan-cho-nguoi-moi-di-lam-2026", "personal-finance-2026-tiet-kiem-tu-dong-high-yield-savings-cd-emergency-fund"],
    "phan-lan-giao-duc-02": ["phan-lan-hanh-phuc-01", "phan-lan-sauna-05"],
    "phan-lan-hanh-phuc-01": ["phan-lan-sauna-05", "phan-lan-giao-duc-02"],
    "phan-lan-sauna-05": ["phan-lan-hanh-phuc-01", "phan-lan-giao-duc-02"],
    "phan-lan-tech-04": ["phan-lan-giao-duc-02", "phan-lan-xanh-03"],
    "phan-lan-xanh-03": ["phan-lan-tech-04", "phan-lan-hanh-phuc-01"],
    "review-noi-chien-khong-dau-2026": ["review-may-rua-bat-gia-dinh-2026", "review-may-pha-ca-phe-gia-dinh-2026"],
    "review-sac-du-phong-di-du-lich-2026": ["balo-cabin-40l-di-han-quoc", "travel-checklist-danh-sach-chuan-bi-truoc-chuyen-di-quoc-te"],
    "routine-buoi-sang-45-phut-nguoi-di-lam": ["meal-prep-5-ngay-nguoi-ban-viet-nam", "don-dep-dien-thoai-1-buoi-tap-trung"],
    "sam-son-bien-thanh-hoa-gan-ha-noi": ["du-lich-da-nang-he-2026-lich-trinh-4-ngay-3-dem", "vietnam-travel-guide-2026"],
    "so-sanh-ve-may-bay-tet-2027": ["kinh-nghiem-du-lich-tet-2027", "review-dat-ve-may-bay-tau-hoa-tet-2027-meo-san-ve-som-khong-bi-ho"],
    "spider-man-brand-new-day-2026-review": ["coyote-vs-acme-2026-review", "review-paradise-2023-nguoi-giau-mua-thoi-gian-song"],
    "supergirl-2026-review": ["coyote-vs-acme-2026-review", "review-super-8-2011-biet-doi-thieu-nien-va-bi-an"],
    "toi-uu-wifi-nha-pho-chung-cu-viet-nam": ["bao-mat-wifi-cong-cong-nguy-co-cach-phong-tranh", "bao-ve-du-lieu-ca-nhan-tren-internet-huong-dan-toan-dien-2026"],
    "vietnam-travel-guide-2026": ["ho-chi-minh-city-3-day-itinerary-first-timer-2026", "cach-viet-visa-itinerary-chuyen-nghiep"],
    "visa-han-bi-tu-choi-ly-do-va-lan-2": ["xin-visa-han-quoc-du-lich-tu-tuc-dien-thu-nhap-8000-usd", "mau-lich-trinh-xin-visa-huong-dan-day-du"],
}

STOP_WORDS = {
    "a", "an", "and", "as", "at", "be", "by", "cho", "cua", "co", "da", "de", "di", "do",
    "duoc", "em", "hay", "in", "is", "khi", "khong", "la", "lam", "mot", "nao", "nen", "nhung",
    "o", "on", "or", "ra", "sau", "the", "thi", "to", "trong", "tu", "va", "ve", "voi", "what",
    "why", "with", "you", "2026", "2027",
}

INTERNAL_LINK_RE = re.compile(
    r"\]\(\s*(?:https?://[^)\s]+)?(?:/reviewchanthat)?/posts/([a-z0-9][a-z0-9\-]*)/?",
    re.I,
)
HEADING_RE = re.compile(r"(?m)^#{2,3}\s+(.+?)\s*$")
TOP_LEVEL_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+\s*=")
TABLE_RE = re.compile(r"^\[\[?[^\]]+\]\]?\s*$")


def now_vietnam() -> datetime:
    return datetime.now(timezone(timedelta(hours=7)))


def split_front_matter(text: str) -> tuple[str, str, str]:
    """Return opening delimiter, TOML front matter, and body.

    The repository policy is TOML.  Failing closed protects articles whose
    front matter should be repaired by the dedicated formatter rather than by
    this focused SEO tool.
    """
    match = re.match(r"^(\+\+\+\r?\n)(.*?)(\r?\n\+\+\+\r?\n?)(.*)$", text, re.S)
    if not match:
        raise ValueError("expected TOML +++ front matter")
    return match.group(1), match.group(2), match.group(4)


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    value = str(value).strip()
    return [value] if value else []


def ascii_text(value: str) -> str:
    value = unicodedata.normalize("NFD", value.lower())
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return value.replace("đ", "d")


def tokens(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", ascii_text(value))
        if len(token) > 2 and token not in STOP_WORDS
    }


def headings(body: str) -> list[str]:
    return [re.sub(r"[*_`]+", "", value).strip() for value in HEADING_RE.findall(body)]


def body_internal_targets(body: str, self_slug: str) -> list[str]:
    targets: list[str] = []
    for match in INTERNAL_LINK_RE.finditer(body):
        target = match.group(1)
        if target != self_slug and target not in targets:
            targets.append(target)
    return targets


def front_matter_targets(meta: dict[str, Any], self_slug: str) -> list[str]:
    targets: list[str] = []
    raw_links = meta.get("internal_links") or []
    if isinstance(raw_links, str):
        raw_links = [raw_links]
    for item in raw_links:
        if not isinstance(item, str):
            continue
        # A scalar is rare but supported for compatibility.
        candidate = Path(item.rstrip("/")).stem
        if candidate != self_slug and candidate not in targets:
            targets.append(candidate)
    for item in raw_links:
        if not isinstance(item, dict):
            continue
        for key in ("ref", "slug", "path", "url"):
            value = item.get(key)
            if value:
                candidate = Path(str(value).rstrip("/")).stem
                if candidate != self_slug and candidate not in targets:
                    targets.append(candidate)
                break
    return targets


def read_posts() -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        opening, fm, body = split_front_matter(text)
        meta = tomllib.loads(fm)
        slug = str(meta.get("slug") or path.stem).strip()
        title = str(meta.get("title") or slug).strip()
        series = as_list(meta.get("series"))
        post = {
            "path": path,
            "text": text,
            "opening": opening,
            "fm": fm,
            "body": body,
            "meta": meta,
            "slug": slug,
            "title": title,
            "seo_title": str(meta.get("seo_title") or "").strip(),
            "description": str(meta.get("description") or "").strip(),
            "categories": as_list(meta.get("categories")),
            "tags": as_list(meta.get("tags")),
            "series": series,
            "draft": bool(meta.get("draft", False)),
            "noindex": bool(meta.get("noindex", False) or meta.get("private", False)),
            "headings": headings(body),
            "body_links": body_internal_targets(body, slug),
            "fm_links": front_matter_targets(meta, slug),
        }
        post["semantic_tokens"] = tokens(
            " ".join(
                [title, post["description"], " ".join(post["categories"]),
                 " ".join(post["tags"]), " ".join(series), " ".join(post["headings"])]
            )
        )
        posts.append(post)
    return posts


def is_indexable(post: dict[str, Any]) -> bool:
    return not post["draft"] and not post["noindex"]


def title_for_serp(post: dict[str, Any]) -> str:
    return post["seo_title"] or post["title"]


def key_line(value: str, key: str) -> str:
    return f"{key} = {json.dumps(value, ensure_ascii=False)}"


def upsert_toml_value(post: dict[str, Any], key: str, value: str | bool) -> None:
    """Surgically change a top-level TOML scalar without reserialising tables."""
    lines = post["fm"].splitlines()
    out: list[str] = []
    wanted = re.compile(rf"^{re.escape(key)}\s*=")
    for line in lines:
        if wanted.match(line):
            continue
        out.append(line)
    line = f"{key} = {'true' if value else 'false'}" if isinstance(value, bool) else key_line(value, key)
    table_index = next((i for i, item in enumerate(out) if TABLE_RE.match(item)), len(out))
    out.insert(table_index, line)
    if table_index < len(out) - 1 and out[table_index + 1].strip():
        out.insert(table_index + 1, "")
    post["fm"] = "\n".join(out).rstrip() + "\n"
    post["meta"][key] = value
    if key == "seo_title":
        post["seo_title"] = str(value)
    elif key == "description":
        post["description"] = str(value)


def render_post(post: dict[str, Any]) -> str:
    return f"{post['opening']}{post['fm']}\n+++\n{post['body']}"


def persist(posts: list[dict[str, Any]], changed: set[str], write: bool) -> None:
    if not write:
        return
    for post in posts:
        if post["slug"] in changed:
            post["path"].write_text(render_post(post), encoding="utf-8")


def make_idf(posts: list[dict[str, Any]]) -> dict[str, float]:
    doc_count = max(1, len(posts))
    frequencies: Counter[str] = Counter()
    for post in posts:
        frequencies.update(post["semantic_tokens"])
    return {token: 1.0 + (doc_count / (1 + count)) ** 0.5 for token, count in frequencies.items()}


def semantic_score(source: dict[str, Any], target: dict[str, Any], idf: dict[str, float]) -> tuple[float, list[str]]:
    if source["slug"] == target["slug"]:
        return -1.0, []
    score = 0.0
    reasons: list[str] = []
    shared_categories = set(source["categories"]) & set(target["categories"])
    shared_tags = set(source["tags"]) & set(target["tags"])
    shared_series = set(source["series"]) & set(target["series"])
    shared_tokens = source["semantic_tokens"] & target["semantic_tokens"]
    if shared_categories:
        score += 8 * len(shared_categories)
        reasons.append("cùng danh mục")
    if shared_tags:
        score += 14 * len(shared_tags)
        reasons.append("cùng nhãn")
    if shared_series:
        score += 28 * len(shared_series)
        reasons.append("cùng series")
    token_score = sum(idf.get(token, 1.0) for token in shared_tokens)
    if token_score:
        score += min(token_score * 1.6, 36)
        reasons.append("thực thể/chủ đề chung")

    # Deliberately narrow cross-category bridges requested for travel↔finance
    # and review↔technology.  A bridge still requires semantic overlap.
    cats = set(source["categories"]) | set(target["categories"])
    travel_finance = {"du-lich", "tai-chinh"}.issubset(cats)
    review_tech = {"review", "cong-nghe"}.issubset(cats)
    bridge_terms = {"chi", "phi", "visa", "ngan", "sach", "iphone", "apple", "wifi", "app", "thiet", "bi"}
    if (travel_finance or review_tech) and (shared_tokens & bridge_terms):
        score += 10
        reasons.append("liên kết liên danh mục")
    return score, reasons


def rank_targets(source: dict[str, Any], candidates: list[dict[str, Any]], idf: dict[str, float]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for target in candidates:
        score, reasons = semantic_score(source, target, idf)
        if score <= 0:
            continue
        # Existing, well-scoped hubs are slightly preferred where they fit.
        if target["slug"] in HUBS.values() and set(source["categories"]) & set(target["categories"]):
            score += 8
            reasons.append("pillar cùng cụm")
        ranked.append({
            "target": target["slug"],
            "title": target["title"],
            "score": round(score, 2),
            "reason": ", ".join(reasons) or "liên quan ngữ nghĩa",
        })
    return sorted(ranked, key=lambda item: (-item["score"], item["target"]))


def build_graph(posts: list[dict[str, Any]]) -> dict[str, Any]:
    indexable = [post for post in posts if is_indexable(post)]
    idf = make_idf(indexable)
    by_slug = {post["slug"]: post for post in indexable}
    links: dict[str, list[dict[str, Any]]] = {}

    def inbound_counts() -> Counter[str]:
        counts: Counter[str] = Counter()
        for targets in links.values():
            counts.update(item["target"] for item in targets)
        return counts

    # A compact graph: only hubs and explicit orphan donors get an end-section
    # card list.  Existing body and front-matter links stay authoritative for
    # the rest of the site, avoiding another six-card block on every article.
    for category, hub_slug in HUBS.items():
        hub = by_slug.get(hub_slug)
        if not hub:
            continue
        ranked = [
            item for item in rank_targets(hub, indexable, idf)
            if category in by_slug[item["target"]]["categories"]
        ]
        links[hub_slug] = ranked[:BASE_GRAPH_LINKS]
        for item in links.get(hub_slug, []):
            satellite = by_slug.get(item["target"])
            if not satellite:
                continue
            bucket = links.setdefault(satellite["slug"], [])
            if any(link["target"] == hub_slug for link in bucket):
                continue
            score, reasons = semantic_score(satellite, hub, idf)
            if score <= 0:
                continue
            if len(bucket) >= MAX_GRAPH_LINKS:
                continue
            bucket.append({
                "target": hub_slug,
                "title": hub["title"],
                "score": round(score + 8, 2),
                "reason": ", ".join(reasons + ["quay về pillar"]) if reasons else "quay về pillar",
            })
            bucket.sort(key=lambda item: (-item["score"], item["target"]))

    # Orphan repair: choose a substantive hub or a strong same-cluster donor;
    # keep each source bounded and leave the related-links UI data-driven.
    inbound = inbound_counts()
    strengths = {
        post["slug"]: (25 if post["slug"] in HUBS.values() else 0) + min(len(post["body"].split()) / 500, 8)
        for post in indexable
    }
    for orphan in indexable:
        if inbound.get(orphan["slug"], 0):
            continue
        donors: list[tuple[float, dict[str, Any], list[str]]] = []
        for donor in indexable:
            score, reasons = semantic_score(donor, orphan, idf)
            if score <= 0:
                continue
            donors.append((score + strengths[donor["slug"]], donor, reasons))
        donors.sort(key=lambda item: (-item[0], item[1]["slug"]))
        if not donors:
            # Same-category fallback remains topical at the taxonomy level.
            donors = [
                (strengths[donor["slug"]], donor, ["cùng danh mục"])
                for donor in indexable
                if donor["slug"] != orphan["slug"] and set(donor["categories"]) & set(orphan["categories"])
            ]
            donors.sort(key=lambda item: (-item[0], item[1]["slug"]))
        for score, donor, reasons in donors:
            bucket = links.setdefault(donor["slug"], [])
            if any(item["target"] == orphan["slug"] for item in bucket):
                break
            if len(bucket) >= MAX_GRAPH_LINKS:
                continue
            bucket.append({
                "target": orphan["slug"],
                "title": orphan["title"],
                "score": round(max(score, 1), 2),
                "reason": ", ".join(reasons + ["sửa orphan"]) if reasons else "sửa orphan",
            })
            bucket.sort(key=lambda item: (-item["score"], item["target"]))
            inbound = inbound_counts()
            break

    inbound = inbound_counts()
    indexable_slugs = sorted(by_slug)
    missing_combined_outbound = sum(
        1 for post in indexable
        if not (post["body_links"] or post["fm_links"] or links.get(post["slug"]))
    )
    return {
        "generated_at": now_vietnam().isoformat(),
        "generator": "semantic-remediation-v1",
        "policy": {
            "max_links_per_source": MAX_GRAPH_LINKS,
            "body_links_are_contextual": True,
            "no_footer_markdown_blocks": True,
            "no_self_links": True,
        },
        "hubs": HUBS,
        "links": links,
        "inbound_counts": {slug: int(inbound.get(slug, 0)) for slug in indexable_slugs},
        "indexable_slugs": indexable_slugs,
        "orphans_after": sum(1 for slug in indexable_slugs if inbound.get(slug, 0) == 0),
        "posts_missing_outbound_after": missing_combined_outbound,
    }


def safe_anchor(title: str) -> str:
    return re.sub(r"[\[\]]", "", title).strip()


def contextual_sentence(target: dict[str, Any], ordinal: int) -> str:
    anchor = f"[{safe_anchor(target['title'])}](/posts/{target['slug']}/)"
    patterns = (
        f"Một lát cắt liên quan là {anchor}, hữu ích khi bạn cần đi sâu vào lựa chọn cụ thể thay vì chỉ dừng ở phần tổng quan.",
        f"Để đối chiếu trước khi quyết định, {anchor} bổ sung bối cảnh thực tế cho đúng vấn đề đang được nhắc tới.",
        f"Nếu tình huống của bạn gần với phần này, {anchor} đi sâu hơn vào tiêu chí và các đánh đổi cần cân nhắc.",
        f"Bạn cũng có thể nối mạch với {anchor} để xem chi tiết chuyên biệt trước khi áp dụng lời khuyên trong bài.",
    )
    return patterns[ordinal % len(patterns)]


def section_insert_position(body: str, target: dict[str, Any]) -> int:
    """Select the most related non-conclusion section, then append one sentence."""
    matches = list(HEADING_RE.finditer(body))
    if not matches:
        paragraphs = list(re.finditer(r"\n\s*\n", body))
        return paragraphs[min(len(paragraphs) - 1, 2)].end() if paragraphs else len(body)
    target_tokens = tokens(" ".join([target["title"], target["description"], " ".join(target["tags"])]))
    choices: list[tuple[float, int]] = []
    for index, match in enumerate(matches):
        heading = match.group(1)
        if any(word in ascii_text(heading) for word in ("ket luan", "ban quyen", "faq")):
            continue
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        segment = body[match.end():next_start].rstrip()
        if len(segment) < 120 or next_start > len(body) * 0.78:
            continue
        score = len(tokens(heading) & target_tokens) * 8 + len(tokens(segment[:900]) & target_tokens)
        # A weak preference avoids stacking new links in the final section.
        score -= max(0, match.start() / max(1, len(body)) - 0.7) * 2
        choices.append((score, len(segment) + match.end()))
    if choices:
        return int(max(choices, key=lambda item: item[0])[1])
    # Never create a disguised footer/end block when headings are sparse.
    # A paragraph around the middle is less perfect semantically but keeps the
    # link in the reading flow rather than after a conclusion.
    middle = len(body) // 2
    breaks = list(re.finditer(r"\n\s*\n", body))
    if breaks:
        return min(breaks, key=lambda item: abs(item.end() - middle)).end()
    return matches[0].end()


def insert_contextual_link(post: dict[str, Any], target: dict[str, Any], ordinal: int) -> bool:
    if target["slug"] in body_internal_targets(post["body"], post["slug"]):
        return False
    position = min(section_insert_position(post["body"], target), len(post["body"]))
    sentence = contextual_sentence(target, ordinal)
    before = post["body"][:position].rstrip()
    after = post["body"][position:]
    post["body"] = f"{before}\n\n{sentence}\n{after}"
    post["body_links"] = body_internal_targets(post["body"], post["slug"])
    return True


def remove_remediation_sentences(post: dict[str, Any]) -> bool:
    patterns = (
        "Một lát cắt liên quan là [",
        "Để đối chiếu trước khi quyết định, [",
        "Nếu tình huống của bạn gần với phần này, [",
        "Bạn cũng có thể nối mạch với [",
    )
    lines = post["body"].splitlines()
    kept = [line for line in lines if not (line.startswith(patterns) and "](/posts/" in line)]
    updated = "\n".join(kept)
    if updated == post["body"]:
        return False
    post["body"] = updated
    post["body_links"] = body_internal_targets(updated, post["slug"])
    return True


def repair_links(posts: list[dict[str, Any]], write: bool, reposition_contextual: bool = False) -> dict[str, Any]:
    indexable = [post for post in posts if is_indexable(post)]
    published = [post for post in posts if not post["draft"]]
    idf = make_idf(published)
    by_slug = {post["slug"]: post for post in indexable}
    by_published_slug = {post["slug"]: post for post in published}
    if reposition_contextual:
        missing = [post for post in published if post["slug"] in CONTEXTUAL_TARGET_OVERRIDES]
        for post in missing:
            remove_remediation_sentences(post)
    else:
        missing = [
            post for post in published
            if not post["body_links"] and not post["fm_links"]
        ]
    changed: set[str] = set()
    repair_rows: list[dict[str, Any]] = []
    for source in missing:
        override = CONTEXTUAL_TARGET_OVERRIDES.get(source["slug"])
        if override:
            unknown = [slug for slug in override if slug not in by_published_slug]
            if unknown:
                raise RuntimeError(f"unknown contextual target(s) for {source['slug']}: {unknown}")
            ranked = [{"target": slug, "score": 100.0} for slug in override]
            target_lookup = by_published_slug
        else:
            ranked = rank_targets(source, indexable, idf)
            target_lookup = by_slug
        selected: list[dict[str, Any]] = []
        for candidate in ranked:
            target = target_lookup[candidate["target"]]
            if candidate["score"] < 10:
                continue
            if insert_contextual_link(source, target, len(selected)):
                selected.append(target)
            if len(selected) == 2:
                break
        # A same-category source always has at least one semantically scored
        # candidate.  Fail loudly rather than inserting an irrelevant link.
        if len(selected) < 2:
            raise RuntimeError(f"could not find two contextual targets for {source['slug']}")
        changed.add(source["slug"])
        repair_rows.append({"source": source["slug"], "targets": [target["slug"] for target in selected]})
    persist(posts, changed, write)
    graph = build_graph(posts)
    if write:
        GRAPH_PATH.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "missing_outbound_before": len(missing),
        "posts_with_contextual_links": len(repair_rows),
        "contextual_links_added": sum(len(row["targets"]) for row in repair_rows),
        "repairs": repair_rows,
        "graph": graph,
    }


def compact_title(slug: str, title: str) -> str:
    if slug in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[slug]
    value = re.sub(r"\s+", " ", title).strip()
    # Prefer complete clauses before trimming words.  This maintains search
    # intent and lets the primary keyword remain at the front.
    candidates = [value]
    for separator in (" — ", ": ", " – "):
        if separator in value:
            candidates.append(value.split(separator, 1)[0].strip())
    for candidate in candidates:
        if TITLE_MIN <= len(candidate) <= TITLE_MAX:
            return candidate
    words = value.split()
    kept: list[str] = []
    for word in words:
        proposal = " ".join(kept + [word])
        if len(proposal) > TITLE_MAX:
            break
        kept.append(word)
    value = " ".join(kept).rstrip(" ,;:–—-")
    # Do not leave a dangling conjunction/preposition in a title tag.
    while value and ascii_text(value.split()[-1]) in {"va", "cho", "tu", "den", "voi", "hay", "or", "and"}:
        value = " ".join(value.split()[:-1])
    if len(value) < TITLE_MIN:
        fallback = re.sub(r"\s+", " ", title).strip()[:TITLE_MAX].rsplit(" ", 1)[0].rstrip(" ,;:–—-")
        value = fallback
    return value


def compact_description(description: str) -> str:
    value = re.sub(r"\s+", " ", description).strip()
    sentences = re.split(r"(?<=[.!?])\s+", value)
    for sentence in sentences:
        if DESCRIPTION_MIN <= len(sentence) <= DESCRIPTION_MAX:
            return sentence
    if len(value) <= DESCRIPTION_MAX:
        return value
    words: list[str] = []
    for word in value.split():
        proposal = " ".join(words + [word])
        if len(proposal) > DESCRIPTION_MAX - 1:
            break
        words.append(word)
    result = " ".join(words).rstrip(" ,;:–—-")
    if result and result[-1] not in ".!?":
        result += "."
    return result


def remediate_metadata(posts: list[dict[str, Any]], write: bool) -> dict[str, Any]:
    changed: set[str] = set()
    title_changes: list[dict[str, Any]] = []
    description_changes: list[dict[str, Any]] = []
    for post in posts:
        if not is_indexable(post):
            continue
        effective_title = title_for_serp(post)
        if not (TITLE_MIN <= len(effective_title) <= TITLE_MAX):
            seo_title = compact_title(post["slug"], post["title"])
            if not (TITLE_MIN <= len(seo_title) <= TITLE_MAX):
                raise RuntimeError(f"invalid SEO title for {post['slug']}: {seo_title!r}")
            if seo_title != post["seo_title"]:
                upsert_toml_value(post, "seo_title", seo_title)
                changed.add(post["slug"])
                title_changes.append({"slug": post["slug"], "seo_title": seo_title, "length": len(seo_title)})
        if post["description"] and not (DESCRIPTION_MIN <= len(post["description"]) <= DESCRIPTION_MAX):
            description = DESCRIPTION_OVERRIDES.get(post["slug"], compact_description(post["description"]))
            if not (DESCRIPTION_MIN <= len(description) <= DESCRIPTION_MAX):
                raise RuntimeError(f"invalid description for {post['slug']}: {description!r}")
            if description != post["description"]:
                upsert_toml_value(post, "description", description)
                changed.add(post["slug"])
                description_changes.append({"slug": post["slug"], "description": description, "length": len(description)})
    persist(posts, changed, write)
    return {
        "seo_titles_fixed": title_changes,
        "descriptions_fixed": description_changes,
        "changed_posts": sorted(changed),
    }


def upgrade_hubs(posts: list[dict[str, Any]], write: bool) -> dict[str, Any]:
    by_slug = {post["slug"]: post for post in posts}
    changed: set[str] = set()
    upgraded: list[dict[str, str]] = []
    for category, slug in HUBS.items():
        post = by_slug.get(slug)
        if not post:
            raise RuntimeError(f"configured hub missing: {slug}")
        if category not in post["categories"]:
            raise RuntimeError(f"configured hub is not in {category}: {slug}")
        if len(post["body"].split()) < 700:
            raise RuntimeError(f"configured hub is too thin: {slug}")
        if not bool(post["meta"].get("pillar")):
            upsert_toml_value(post, "pillar", True)
            changed.add(slug)
        upgraded.append({"category": category, "slug": slug, "title": post["title"]})
    persist(posts, changed, write)
    return {"upgraded": upgraded, "changed_posts": sorted(changed)}


def graph_metrics(posts: list[dict[str, Any]], graph: dict[str, Any] | None = None) -> dict[str, Any]:
    indexable = [post for post in posts if is_indexable(post)]
    if graph is None and GRAPH_PATH.exists():
        graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    graph = graph or {"links": {}, "inbound_counts": {}}
    graph_links = graph.get("links") or {}
    graph_inbound = graph.get("inbound_counts") or {}
    all_slugs = {post["slug"] for post in indexable}
    inbound: Counter[str] = Counter()
    missing_outbound: list[str] = []
    total_outbound = 0
    for post in indexable:
        generated = [str(item.get("target")) for item in graph_links.get(post["slug"], []) if isinstance(item, dict)]
        targets = list(dict.fromkeys(post["body_links"] + post["fm_links"] + generated))
        targets = [target for target in targets if target in all_slugs and target != post["slug"]]
        total_outbound += len(targets)
        inbound.update(targets)
        if not targets:
            missing_outbound.append(post["slug"])
    for slug, count in graph_inbound.items():
        inbound[slug] = max(inbound[slug], int(count))
    orphan = [post["slug"] for post in indexable if inbound.get(post["slug"], 0) == 0]
    title_violations = [post["slug"] for post in indexable if not (TITLE_MIN <= len(title_for_serp(post)) <= TITLE_MAX)]
    description_violations = [post["slug"] for post in indexable if post["description"] and not (DESCRIPTION_MIN <= len(post["description"]) <= DESCRIPTION_MAX)]
    # A bounded, interpretable score is preferable to a magic aggregate: 40%
    # inbound coverage, 30% outbound coverage, 15% title and 15% description.
    n = max(1, len(indexable))
    score = round(
        40 * (1 - len(orphan) / n)
        + 30 * (1 - len(missing_outbound) / n)
        + 15 * (1 - len(title_violations) / n)
        + 15 * (1 - len(description_violations) / n),
        2,
    )
    return {
        "indexable_posts": len(indexable),
        "orphan_inbound": len(orphan),
        "missing_outbound": len(missing_outbound),
        "title_violations": len(title_violations),
        "description_violations": len(description_violations),
        "total_outbound": total_outbound,
        "average_outbound": round(total_outbound / n, 2),
        "link_graph_score": score,
        "orphans": orphan,
        "posts_without_outbound": missing_outbound,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded SEO remediation")
    parser.add_argument("command", choices=("links", "metadata", "hubs", "report", "all"))
    parser.add_argument("--write", action="store_true", help="Apply changes; default is a dry run")
    parser.add_argument(
        "--reposition-contextual",
        action="store_true",
        help="Move this tool's contextual links back into article sections (links only)",
    )
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args()

    posts = read_posts()
    before = graph_metrics(posts)
    result: dict[str, Any] = {"before": before, "mode": "write" if args.write else "dry-run"}
    if args.command in {"hubs", "all"}:
        result["hubs"] = upgrade_hubs(posts, args.write)
    if args.command in {"links", "all"}:
        result["links"] = repair_links(posts, args.write, args.reposition_contextual)
    if args.command in {"metadata", "all"}:
        result["metadata"] = remediate_metadata(posts, args.write)
    if args.command == "report":
        result["graph"] = json.loads(GRAPH_PATH.read_text(encoding="utf-8")) if GRAPH_PATH.exists() else {}
    if args.write and args.command in {"links", "all"}:
        # Metadata does not alter the graph.  Hubs do, therefore regenerate
        # once more after all mutations for the final canonical data file.
        graph = build_graph(posts)
        GRAPH_PATH.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    final_graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8")) if GRAPH_PATH.exists() else None
    result["after"] = graph_metrics(posts, final_graph)
    result["generated_at"] = now_vietnam().isoformat()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"before": before, "after": result["after"]}, ensure_ascii=False, indent=2))
    print(f"Report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
