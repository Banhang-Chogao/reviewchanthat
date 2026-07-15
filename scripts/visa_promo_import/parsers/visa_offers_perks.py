"""
Visa Offers & Perks parser (official portal).

Primary crawler: Playwright (Selenium fallback) — networkidle, scroll, load-more,
collect EVERY listing card detail URL, visit EACH detail page, parse fields.

Does NOT rely on fragile CSS class names; prefers semantic selectors
(article, a[href*="/visa-offers-and-perks/"], roles, text, DOM hierarchy).

Example:
  https://www.visa.com.vn/vi_vn/visa-offers-and-perks/?cardProduct=65&paymentType=9
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

from ..allowlist import assert_allowed_url
from ..crawl_report import CrawlReport, format_report_text
from ..fetcher import BrowserCrawlSession, ListingLink, http_get, http_post_json
from ..normalize import normalize_promotion
from .base import BasePromotionParser, ParseContext, ParsedBatch

logger = logging.getLogger(__name__)

DEFAULT_CATEGORY_LABELS = {
    "18": "Travel",
    "26": "Hotel",
    "115": "Lifestyle",
    "132": "Other",
    "94": "Dining",
}

CARD_LEVEL_HINTS = (
    ("Infinite", "Infinite"),
    ("Signature", "Signature"),
    ("Platinum", "Platinum"),
    ("Gold", "Gold"),
    ("Classic", "Classic"),
    ("Private", "Infinite"),
    ("Privilege", "Infinite"),
)

DETAIL_PATH_RE = re.compile(r"/visa-offers-and-perks/([^/]+)/(\d+)", re.I)
MONEY_RE = re.compile(
    r"(?:tối đa|toi da|maximum|cap|lên đến|len den|không quá|khong qua)?\s*"
    r"(\d[\d.,]*)\s*(?:₫|đ|vnd|vnđ|dong)",
    re.I,
)
MIN_SPEND_RE = re.compile(
    r"(?:tối thiểu|toi thieu|minimum|min\.?|trên|tren|từ|tu)\s*"
    r"(\d[\d.,]*)\s*(?:₫|đ|vnd|vnđ)?",
    re.I,
)
DATE_RANGE_RE = re.compile(
    r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\s*[-–—đếnto]+\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
    re.I,
)


class VisaOffersPerksParser(BasePromotionParser):
    name = "visa_offers_perks"

    @classmethod
    def supports(cls, url: str) -> bool:
        try:
            u = urlparse(url.strip())
        except Exception:
            return False
        host = (u.hostname or "").lower()
        if not (
            host == "visa.com"
            or host.endswith(".visa.com")
            or host == "visa.com.vn"
            or host.endswith(".visa.com.vn")
        ):
            return False
        path = (u.path or "").lower()
        return (
            "visa-offers-and-perks" in path
            or "promociones" in path
            or "visa-commercial-offers" in path
        )

    def parse(self, ctx: ParseContext) -> ParsedBatch:
        source = assert_allowed_url(ctx.source_url)
        u = urlparse(source)
        origin = f"{u.scheme}://{u.netloc}"
        locale = self._locale_from_path(u.path) or "vi_vn"
        qs = parse_qs(u.query)
        card_products = qs.get("cardProduct") or qs.get("cardProductTypes") or []
        payment_types = qs.get("paymentType") or qs.get("cardPaymentTypes") or []

        report = CrawlReport(source_url=source, parser=self.name)
        report.log(f"Start crawl · locale={locale} · filters cardProduct={card_products} paymentType={payment_types}")

        # Primary: Playwright browser crawl (listing scroll → detail pages)
        try:
            promotions, report = self._crawl_with_browser(
                source_url=source,
                origin=origin,
                locale=locale,
                card_products=card_products,
                payment_types=payment_types,
                skip_expired=ctx.skip_expired,
                report=report,
            )
        except Exception as browser_err:  # noqa: BLE001
            report.log(f"Browser crawl failed: {browser_err}")
            report.warnings.append(f"Browser crawl failed ({browser_err}); trying API-assisted fallback.")
            logger.warning("Browser crawl failed: %s", browser_err)
            try:
                promotions, report = self._crawl_api_assisted(
                    source_url=source,
                    origin=origin,
                    locale=locale,
                    card_products=card_products,
                    payment_types=payment_types,
                    skip_expired=ctx.skip_expired,
                    report=report,
                )
            except Exception as api_err:  # noqa: BLE001
                report.status = "failed"
                report.errors.append(str(browser_err))
                report.errors.append(str(api_err))
                raise RuntimeError(
                    f"Could not extract Visa offers from {source}. "
                    f"Browser: {browser_err}; API fallback: {api_err}"
                ) from api_err

        # Integrity: listing vs visited vs parsed
        report._parsed_source_ids = {  # type: ignore[attr-defined]
            str(p.get("PromotionID") or "").replace("visa-", "")
            for p in promotions
            if p.get("PromotionID")
        }
        report.parsed_merchants = [str(p.get("Merchant") or "") for p in promotions]
        report.finalize(
            listing_count=report.listing_promotions_found or len(report.listing_cards),
            visited_count=report.detail_pages_visited,
            parsed_count=len(promotions),
            duplicates_removed=report.duplicates_removed,
        )

        # Starbucks (dynamic): listing has it but parsed set does not → FAILED, block import
        import_blocked = bool(report.starbucks_check_failed)
        if import_blocked:
            report.errors.append(
                "Import halted: listing contains a merchant (Starbucks) that is missing from "
                "the parsed/import set. See missing_promotions."
            )
            report.log("IMPORT STOPPED — Starbucks integrity failure")
            return ParsedBatch(
                promotions=[],
                source_url=source,
                parser=self.name,
                engine=report.engine,
                warnings=report.warnings + report.errors,
                meta={
                    "crawl_report": report.as_dict(),
                    "crawl_report_text": format_report_text(report),
                    "import_blocked": True,
                    "locale": locale,
                    "cardProduct": card_products,
                    "paymentType": payment_types,
                },
            )

        # Count mismatch: do NOT silently ignore — surface missing list loudly.
        # Still continue with remaining valid promotions (detail failures already retried).
        if report.count_mismatch or report.missing_promotions:
            report.warnings.append(
                "Listing/detail/import count mismatch — missing promotions listed in crawl report. "
                "Importing remaining valid promotions only."
            )
            report.log(
                "Count mismatch reported (import continues with valid rows): "
                + "; ".join(report.missing_promotions[:8])
            )

        if ctx.skip_expired:
            before = len(promotions)
            promotions = [p for p in promotions if p.get("Status") != "Expired"]
            if len(promotions) < before:
                report.warnings.append(f"Skipped {before - len(promotions)} expired after parse")

        return ParsedBatch(
            promotions=promotions,
            source_url=source,
            parser=self.name,
            engine=report.engine,
            warnings=report.warnings,
            meta={
                "crawl_report": report.as_dict(),
                "crawl_report_text": format_report_text(report),
                "import_blocked": False,
                "locale": locale,
                "cardProduct": card_products,
                "paymentType": payment_types,
                "count": len(promotions),
            },
        )

    # ── Primary: Playwright / Selenium browser crawl ─────────────────────────

    def _crawl_with_browser(
        self,
        *,
        source_url: str,
        origin: str,
        locale: str,
        card_products: List[str],
        payment_types: List[str],
        skip_expired: bool,
        report: CrawlReport,
    ) -> Tuple[List[Dict[str, Any]], CrawlReport]:
        promotions: List[Dict[str, Any]] = []
        with BrowserCrawlSession(log=report.log) as session:
            report.engine = session.engine
            session.goto(source_url, timeout_ms=90000)
            session.wait_for_promotion_cards(timeout_ms=30000)
            session.auto_scroll_until_stable(max_rounds=40, pause_ms=850, stable_rounds=3)
            links = session.collect_listing_links(source_url)
            if not links:
                raise RuntimeError("No promotion cards found after scroll/load-more on listing page")

            report.listing_cards = [
                {
                    "detail_url": L.detail_url,
                    "source_id": L.source_id,
                    "merchant": L.merchant,
                    "title": L.title,
                    "slug": L.slug,
                }
                for L in links
            ]
            report.listing_promotions_found = len(links)
            report.log(f"Listing cards discovered: {len(links)}")

            visited = 0
            parsed: List[Dict[str, Any]] = []
            seen_ids: set[str] = set()
            dupes = 0

            for idx, link in enumerate(links, start=1):
                report.log(f"[{idx}/{len(links)}] Detail page → {link.detail_url}")
                promo, err = self._fetch_and_parse_detail(
                    session=session,
                    link=link,
                    origin=origin,
                    locale=locale,
                    source_url=source_url,
                    retries=3,
                    report=report,
                )
                visited += 1
                if err:
                    report.failed_urls.append(f"{link.detail_url} · {err}")
                    report.log(f"  FAILED after retries: {err}")
                    continue
                if not promo:
                    report.failed_urls.append(f"{link.detail_url} · empty parse")
                    continue
                if skip_expired and promo.get("Status") == "Expired":
                    report.log(f"  skipped expired: {promo.get('Merchant')}")
                    continue
                pid = str(promo.get("PromotionID") or "")
                if pid and pid in seen_ids:
                    dupes += 1
                    report.log(f"  duplicate removed: {pid}")
                    continue
                if pid:
                    seen_ids.add(pid)
                parsed.append(promo)
                report.log(
                    f"  OK · {promo.get('Merchant')} · {promo.get('OfferTitle', '')[:60]}"
                )

            report.detail_pages_visited = visited
            report.duplicates_removed = dupes
            promotions = parsed

        return promotions, report

    def _fetch_and_parse_detail(
        self,
        *,
        session: Optional[BrowserCrawlSession],
        link: ListingLink,
        origin: str,
        locale: str,
        source_url: str,
        retries: int,
        report: CrawlReport,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        last_err: Optional[str] = None
        for attempt in range(1, retries + 1):
            try:
                # Prefer structured detail API (same data the SPA uses), then enrich with page text
                api_raw = None
                try:
                    api_raw = self._fetch_detail_api(
                        origin=origin, locale=locale, source_id=link.source_id, referer=link.detail_url
                    )
                    report.log(f"  detail API ok (attempt {attempt})")
                except Exception as api_exc:  # noqa: BLE001
                    report.log(f"  detail API miss (attempt {attempt}): {api_exc}")

                page_text = ""
                images: List[str] = []
                if session is not None:
                    session.goto(link.detail_url, timeout_ms=60000)
                    # Wait for main content
                    try:
                        session.wait_for_promotion_cards(timeout_ms=8000)
                    except Exception:
                        pass
                    session._impl.wait_ms(1200)  # type: ignore[attr-defined]
                    page_text, _html = session.page_text_and_html()
                    images = session.page_images()
                    report.log(f"  detail page rendered · text_len={len(page_text)}")
                else:
                    # No browser: try plain GET (SPA shell) — rely on API
                    pass

                promo = self._parse_detail_to_schema(
                    link=link,
                    api_raw=api_raw,
                    page_text=page_text,
                    images=images,
                    source_url=source_url,
                    locale=locale,
                )
                if promo and promo.get("OfferTitle"):
                    return promo, None
                last_err = "parsed empty OfferTitle"
            except Exception as exc:  # noqa: BLE001
                last_err = str(exc)
                report.log(f"  attempt {attempt}/{retries} error: {exc}")
            # Exponential backoff
            if attempt < retries:
                delay = (2 ** attempt) + (0.1 * attempt)
                report.log(f"  backoff {delay:.1f}s before retry")
                time.sleep(delay)
        return None, last_err or "unknown detail failure"

    def _fetch_detail_api(
        self,
        *,
        origin: str,
        locale: str,
        source_id: str,
        referer: str,
    ) -> Dict[str, Any]:
        if not source_id:
            raise RuntimeError("missing source_id")
        endpoint = f"{origin}/offers/api/offer/{source_id}?locale={locale}&siteId={urlparse(origin).hostname}"
        assert_allowed_url(endpoint.split("?")[0])
        fr = http_get(endpoint, referer=referer, timeout=40.0, retries=2)
        data = fr.json_data
        if not isinstance(data, dict) or not data.get("offerId"):
            raise RuntimeError("detail API returned non-offer JSON")
        return data

    def _parse_detail_to_schema(
        self,
        *,
        link: ListingLink,
        api_raw: Optional[Dict[str, Any]],
        page_text: str,
        images: List[str],
        source_url: str,
        locale: str,
    ) -> Dict[str, Any]:
        merchant = link.merchant
        title = link.title
        desc = ""
        terms = ""
        start = ""
        end = ""
        eligible = ""
        category = ""
        country = "Vietnam" if "vi_" in locale.lower() else ""
        logo = ""
        banner = ""
        apply_url = link.detail_url
        card_level = ""
        source_id = link.source_id

        if api_raw:
            source_id = str(api_raw.get("offerId") or source_id)
            merchants = api_raw.get("merchantList") or []
            if merchants and isinstance(merchants[0], dict):
                merchant = (merchants[0].get("merchant") or merchant or "").strip()
                mimgs = merchants[0].get("merchantImages") or []
                if mimgs and isinstance(mimgs[0], dict):
                    logo = mimgs[0].get("fileLocation") or logo
            short = api_raw.get("offerShortDescription") or {}
            if isinstance(short, dict):
                desc = (short.get("text") or "").strip()
            elif isinstance(short, str):
                desc = short.strip()
            offer_title = (api_raw.get("offerTitle") or "").strip()
            title = offer_title or desc or merchant or title
            # Prefer description as offer title when title equals merchant
            if title == merchant and desc:
                title = desc[:160]
            copy = api_raw.get("offerCopy") or {}
            if isinstance(copy, dict):
                terms = (copy.get("text") or "").strip()
                if not terms and copy.get("richText"):
                    terms = re.sub(r"<[^>]+>", " ", str(copy.get("richText")))
                    terms = re.sub(r"\s+", " ", terms).strip()
            elif isinstance(copy, str):
                terms = copy.strip()
            legal = api_raw.get("merchantTerms") or api_raw.get("visaTerms") or ""
            if isinstance(legal, dict):
                legal = legal.get("text") or ""
            if legal:
                terms = (terms + "\n" + str(legal)).strip()

            start = (
                api_raw.get("validityFromDateTime")
                or api_raw.get("promotionFromDateTime")
                or api_raw.get("validityFromDate")
                or ""
            )
            end = (
                api_raw.get("validityToDateTime")
                or api_raw.get("promotionToDateTime")
                or api_raw.get("validityToDate")
                or ""
            )
            start = self._parse_visa_date(start)
            end = self._parse_visa_date(end)

            cards = api_raw.get("cardProductList") or []
            eligible_parts = []
            for c in cards:
                if isinstance(c, dict):
                    eligible_parts.append(str(c.get("value") or c.get("key") or ""))
            eligible = ", ".join(p for p in eligible_parts if p)

            cats = api_raw.get("categorySubcategoryList") or []
            if cats and isinstance(cats[0], dict):
                category = str(cats[0].get("value") or "")
            countries = api_raw.get("redemptionCountries") or api_raw.get("promotingCountries") or []
            if countries and isinstance(countries[0], dict):
                country = str(countries[0].get("value") or country)
            imgs = api_raw.get("imageList") or []
            if imgs and isinstance(imgs[0], dict):
                banner = imgs[0].get("fileLocation") or banner
            redemption = (api_raw.get("redemptionUrl") or "").strip()
            if redemption and redemption.startswith("https://"):
                try:
                    assert_allowed_url(redemption.split("?")[0])
                    # Keep official Visa detail as ApplyURL; store partner link in terms note if external
                    if "visa.com" in redemption:
                        apply_url = redemption.split("?")[0]
                except Exception:
                    pass

        # Merge page text (Playwright) when API sparse
        blob = page_text or ""
        if blob:
            if not desc:
                # First non-empty substantial line after merchant
                for line in blob.splitlines():
                    line = line.strip()
                    if len(line) > 20 and merchant.lower() not in line.lower()[: len(merchant) + 2]:
                        desc = line[:300]
                        break
            if not terms or len(terms) < 40:
                # Capture terms-heavy section
                if "điều khoản" in blob.lower() or "terms" in blob.lower() or "chương trình" in blob.lower():
                    terms = (terms + "\n" + blob[:6000]).strip()
                else:
                    terms = (terms + "\n" + blob[:4000]).strip()
            if not start or not end:
                m = DATE_RANGE_RE.search(blob)
                if m:
                    if not start:
                        start = m.group(1)
                    if not end:
                        end = m.group(2)
            if not eligible:
                # Heuristic from text
                levels = []
                for needle, level in CARD_LEVEL_HINTS:
                    if re.search(rf"\bvisa\s+{re.escape(needle)}\b", blob, re.I):
                        levels.append(f"Visa {level}")
                eligible = ", ".join(dict.fromkeys(levels))

        if not title:
            title = desc[:160] or merchant or link.slug
        if title == merchant and desc:
            title = desc[:160]

        cashback_cap = 0.0
        min_spend = 0.0
        search_blob = f"{title} {desc} {terms}"
        for m in MONEY_RE.finditer(search_blob):
            # Prefer lines mentioning cap/max for cashback_cap
            span_start = max(0, m.start() - 40)
            ctx = search_blob[span_start : m.end() + 5].lower()
            val = self._to_float(m.group(1))
            if any(k in ctx for k in ("tối đa", "toi da", "maximum", "cap", "lên đến", "len den")):
                cashback_cap = max(cashback_cap, val)
            elif any(k in ctx for k in ("tối thiểu", "toi thieu", "minimum", "min", "trên", "tren")):
                min_spend = max(min_spend, val)
        m2 = MIN_SPEND_RE.search(search_blob)
        if m2 and not min_spend:
            min_spend = self._to_float(m2.group(1))

        for needle, level in CARD_LEVEL_HINTS:
            if needle.lower() in (eligible + " " + search_blob).lower():
                card_level = level
                break

        # Images: logo/banner from API or page
        if not logo and images:
            for img in images:
                if "logo" in img.lower() or "merchant" in img.lower():
                    logo = img
                    break
            if not logo:
                logo = images[0]
        if not banner and images:
            for img in images:
                if img != logo and "logo" not in img.lower():
                    banner = img
                    break

        pid = f"visa-{source_id}" if source_id else ""

        return normalize_promotion(
            {
                "PromotionID": pid,
                "Bank": "Visa",
                "Card": "",
                "CardLevel": card_level,
                "Merchant": merchant or "Visa Partner",
                "MerchantCategory": category or self._guess_category(merchant, title, desc),
                "PromotionType": "Discount",
                "OfferTitle": title,
                "ShortDescription": desc or title,
                "CashbackCap": cashback_cap,
                "MinimumSpend": min_spend,
                "EligibleCards": eligible,
                "StartDate": start,
                "EndDate": end,
                "ApplyURL": apply_url or link.detail_url,
                "OfficialSource": "Visa Offers & Perks",
                "Terms": (terms or "")[:4000],
                "Featured": False,
                "Logo": logo,
                "Banner": banner,
                "SourceURL": source_url,
                "Status": "Active",
                "Country": country or "Vietnam",
                "Priority": 50,
                "Images": images[:8],
            },
            source_url=source_url,
        )

    # ── Fallback: API listing + detail API (still visits every detail) ───────

    def _crawl_api_assisted(
        self,
        *,
        source_url: str,
        origin: str,
        locale: str,
        card_products: List[str],
        payment_types: List[str],
        skip_expired: bool,
        report: CrawlReport,
    ) -> Tuple[List[Dict[str, Any]], CrawlReport]:
        report.log("API-assisted fallback: listing via perks API, then each detail")
        report.engine = (report.engine or "") + "+api-fallback" if report.engine else "api-fallback"

        site_id = urlparse(origin).hostname or "www.visa.com.vn"
        endpoint = f"{origin}/offers/api/portal/portal/perks/"
        assert_allowed_url(endpoint)
        body = {
            "siteId": site_id,
            "perkTypeRequests": [
                {
                    "requestIdentifier": None,
                    "perkType": "OFFERS",
                    "locale": locale,
                    "pageRequest": {"index": 0, "limit": 1000},
                    "perkArguments": {"offerType": "U"},
                }
            ],
        }
        result = http_post_json(endpoint, body, referer=source_url, timeout=45.0, retries=3)
        data = result.json_data
        if not isinstance(data, dict):
            raise RuntimeError("Perks API returned non-JSON")
        groups = data.get("perksGroups") or []
        if not groups:
            raise RuntimeError("Perks API returned empty perksGroups")

        raw_perks: List[Dict[str, Any]] = []
        for g in groups:
            for perk in g.get("perks") or []:
                raw_perks.append(perk)
        report.log(f"Perks API returned {len(raw_perks)} offers")

        # Client-side filter matching SPA query params
        if card_products:
            want = {str(x) for x in card_products}
            filtered = []
            for p in raw_perks:
                md = p.get("metaData") or {}
                types = {str(x) for x in (md.get("cardProductTypes") or [])}
                if not types or types & want:
                    filtered.append(p)
            if filtered:
                raw_perks = filtered
                report.log(f"After cardProduct filter: {len(raw_perks)}")
        if payment_types:
            want = {str(x) for x in payment_types}
            filtered = []
            for p in raw_perks:
                md = p.get("metaData") or {}
                types = {str(x) for x in (md.get("cardPaymentTypes") or [])}
                if not types or types & want:
                    filtered.append(p)
            if filtered:
                raw_perks = filtered
                report.log(f"After paymentType filter: {len(raw_perks)}")

        links: List[ListingLink] = []
        for perk in raw_perks:
            sid = str(perk.get("sourceId") or "")
            merchant = (perk.get("merchantName") or perk.get("title") or "").strip()
            slug = re.sub(r"[^a-z0-9]+", "-", merchant.lower()).strip("-") or "offer"
            detail = f"{origin}/{locale}/visa-offers-and-perks/{slug}/{sid}" if sid else source_url
            links.append(
                ListingLink(
                    detail_url=detail,
                    source_id=sid,
                    slug=slug,
                    merchant=merchant,
                    title=(perk.get("title") or merchant or "").strip(),
                )
            )

        report.listing_cards = [
            {
                "detail_url": L.detail_url,
                "source_id": L.source_id,
                "merchant": L.merchant,
                "title": L.title,
                "slug": L.slug,
            }
            for L in links
        ]
        report.listing_promotions_found = len(links)

        # Try browser for detail pages; if unavailable parse via detail API only
        session: Optional[BrowserCrawlSession] = None
        try:
            session = BrowserCrawlSession(log=report.log)
            session.__enter__()
            report.engine = session.engine + "+api-listing"
        except Exception as exc:  # noqa: BLE001
            report.log(f"No browser for detail visits ({exc}); detail API only")
            session = None

        parsed: List[Dict[str, Any]] = []
        visited = 0
        seen: set[str] = set()
        dupes = 0
        try:
            for idx, link in enumerate(links, start=1):
                report.log(f"[fallback {idx}/{len(links)}] {link.detail_url}")
                promo, err = self._fetch_and_parse_detail(
                    session=session,
                    link=link,
                    origin=origin,
                    locale=locale,
                    source_url=source_url,
                    retries=3,
                    report=report,
                )
                visited += 1
                if err or not promo:
                    report.failed_urls.append(f"{link.detail_url} · {err or 'empty'}")
                    continue
                if skip_expired and promo.get("Status") == "Expired":
                    continue
                pid = str(promo.get("PromotionID") or "")
                if pid and pid in seen:
                    dupes += 1
                    continue
                if pid:
                    seen.add(pid)
                parsed.append(promo)
        finally:
            if session is not None:
                session.__exit__(None, None, None)

        report.detail_pages_visited = visited
        report.duplicates_removed = dupes
        return parsed, report

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _locale_from_path(path: str) -> Optional[str]:
        m = re.search(r"/([a-z]{2}_[a-z]{2})/", path or "", re.I)
        return m.group(1) if m else None

    @staticmethod
    def _to_float(s: str) -> float:
        s = re.sub(r"[^\d.,]", "", s or "")
        if not s:
            return 0.0
        if s.count(".") > 1:
            s = s.replace(".", "")
        s = s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_visa_date(v: Any) -> str:
        if v is None or v == "":
            return ""
        if isinstance(v, (int, float)):
            n = float(v)
            if n > 1e12:
                n /= 1000.0
            try:
                return datetime.utcfromtimestamp(n).date().isoformat()
            except (OverflowError, OSError, ValueError):
                return ""
        s = str(v).strip()
        # "Mar 30, 2026 17:00 GMT"
        for fmt in (
            "%b %d, %Y %H:%M %Z",
            "%b %d, %Y %H:%M GMT",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
        ):
            try:
                # normalize GMT token
                ss = s.replace(" GMT", " GMT")
                if fmt.endswith("%Z") or "GMT" in fmt:
                    ss = re.sub(r"\s+GMT$", "", s, flags=re.I)
                    return datetime.strptime(ss, "%b %d, %Y %H:%M").date().isoformat()
                return datetime.strptime(s[:26], fmt).date().isoformat()
            except ValueError:
                continue
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        return ""

    @staticmethod
    def _guess_category(merchant: str, title: str, desc: str) -> str:
        blob = f"{merchant} {title} {desc}".lower()
        if any(k in blob for k in ("starbucks", "coffee", "café", "cafe", "ẩm thực", "dining", "restaurant", "food")):
            return "Dining" if "starbucks" not in blob and "coffee" not in blob else "Coffee"
        if any(k in blob for k in ("hotel", "resort", "khách sạn", "marriott", "hilton", "ihg", "accor")):
            return "Hotel"
        if any(k in blob for k in ("flight", "travel", "klook", "agoda", "booking", "du lịch")):
            return "Travel"
        if any(k in blob for k in ("cgv", "movie", "phim", "entertainment")):
            return "Entertainment"
        if any(k in blob for k in ("shop", "mua sắm", "mall", "acfc")):
            return "Shopping"
        return "Other"
