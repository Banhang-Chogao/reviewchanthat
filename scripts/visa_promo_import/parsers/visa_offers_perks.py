"""
Visa Offers & Perks parser (official portal).

Uses Visa's public perks listing JSON API (semantic data) instead of brittle
CSS selectors. Falls back to rendered HTML / markdown-like structure when needed.

Example:
  https://www.visa.com.vn/vi_vn/visa-offers-and-perks/?cardProduct=65&paymentType=9
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

from ..allowlist import assert_allowed_url
from ..fetcher import fetch_rendered_html, http_post_json
from ..normalize import normalize_promotion
from .base import BasePromotionParser, ParseContext, ParsedBatch

# Category id → internal (from portal metadata; extended at runtime when available)
DEFAULT_CATEGORY_LABELS = {
    "18": "Travel",
    "26": "Hotel",
    "115": "Lifestyle",
    "132": "Other",
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


class VisaOffersPerksParser(BasePromotionParser):
    name = "visa_offers_perks"

    @classmethod
    def supports(cls, url: str) -> bool:
        try:
            u = urlparse(url.strip())
        except Exception:
            return False
        host = (u.hostname or "").lower()
        if not (host == "visa.com" or host.endswith(".visa.com") or host == "visa.com.vn" or host.endswith(".visa.com.vn")):
            return False
        path = (u.path or "").lower()
        return "visa-offers-and-perks" in path or "promociones" in path or "visa-commercial-offers" in path

    def parse(self, ctx: ParseContext) -> ParsedBatch:
        source = assert_allowed_url(ctx.source_url)
        u = urlparse(source)
        origin = f"{u.scheme}://{u.netloc}"
        locale = self._locale_from_path(u.path) or "vi_vn"
        qs = parse_qs(u.query)
        card_products = qs.get("cardProduct") or qs.get("cardProductTypes") or []
        payment_types = qs.get("paymentType") or qs.get("cardPaymentTypes") or []

        warnings: List[str] = []
        engine = "httpx"
        raw_promos: List[Dict[str, Any]] = []
        meta_labels: Dict[str, Dict[str, str]] = {}

        try:
            raw_promos, meta_labels, engine = self._fetch_via_api(
                origin=origin,
                locale=locale,
                referer=source,
            )
        except Exception as api_err:  # noqa: BLE001
            warnings.append(f"API path failed ({api_err}); trying rendered page.")
            try:
                raw_promos, engine = self._fetch_via_rendered(source)
            except Exception as ren_err:  # noqa: BLE001
                raise RuntimeError(
                    f"Could not extract Visa offers from {source}. "
                    f"API: {api_err}; Render: {ren_err}"
                ) from ren_err

        # Client-side filter from query params (API filter body is unreliable)
        if card_products:
            want = {str(x) for x in card_products}
            filtered = []
            for p in raw_promos:
                types = set(str(x) for x in (p.get("_cardProductTypes") or []))
                if not types or types & want:
                    filtered.append(p)
            if filtered:
                raw_promos = filtered
            else:
                warnings.append(
                    "No offers matched cardProduct filter; returning unfiltered page results."
                )
        if payment_types:
            want = {str(x) for x in payment_types}
            filtered = []
            for p in raw_promos:
                types = set(str(x) for x in (p.get("_cardPaymentTypes") or []))
                if not types or types & want:
                    filtered.append(p)
            if filtered:
                raw_promos = filtered

        promotions: List[Dict[str, Any]] = []
        for raw in raw_promos:
            promo = self._to_schema(raw, source_url=source, meta_labels=meta_labels, locale=locale)
            if not promo.get("OfferTitle"):
                continue
            if ctx.skip_expired and promo.get("Status") == "Expired":
                continue
            promotions.append(promo)

        return ParsedBatch(
            promotions=promotions,
            source_url=source,
            parser=self.name,
            engine=engine,
            warnings=warnings,
            meta={
                "locale": locale,
                "cardProduct": card_products,
                "paymentType": payment_types,
                "count": len(promotions),
            },
        )

    def _fetch_via_api(
        self,
        *,
        origin: str,
        locale: str,
        referer: str,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, str]], str]:
        site_id = urlparse(origin).hostname or "www.visa.com.vn"
        endpoint = f"{origin}/offers/api/portal/portal/perks/"
        assert_allowed_url(endpoint)

        body = {
            "siteId": site_id,
            "perkTypeRequests": [
                {
                    "perkType": "OFFERS",
                    "locale": locale,
                    "pageRequest": {"index": 0, "limit": 200},
                }
            ],
        }
        result = http_post_json(endpoint, body, referer=referer, timeout=45.0, retries=3)
        data = result.json_data
        if not isinstance(data, dict):
            raise RuntimeError("Perks API returned non-JSON")
        groups = data.get("perksGroups") or []
        if not groups:
            raise RuntimeError("Perks API returned empty perksGroups")

        meta_labels = self._labels_from_metadata(groups[0].get("metadataDefinition") or [])
        out: List[Dict[str, Any]] = []
        for g in groups:
            for perk in g.get("perks") or []:
                out.append(self._map_api_perk(perk, origin=origin, locale=locale))
        if not out:
            raise RuntimeError("Perks API returned zero offers")
        return out, meta_labels, result.engine

    def _fetch_via_rendered(self, source: str) -> Tuple[List[Dict[str, Any]], str]:
        """Fallback: JS-rendered listing → extract offer detail links + titles."""
        fr = fetch_rendered_html(
            source,
            wait_selector="[data-area='offer_list_container'], vs-global-offers, a[href*='visa-offers-and-perks']",
            wait_ms=3000,
        )
        html = fr.body or ""
        # Never execute remote scripts — BeautifulSoup text parse only
        try:
            from bs4 import BeautifulSoup  # type: ignore

            soup = BeautifulSoup(html, "lxml")
            for tag in soup(["script", "style", "noscript", "iframe"]):
                tag.decompose()
            links = []
            for a in soup.find_all("a", href=True):
                href = a.get("href") or ""
                text = a.get_text(" ", strip=True)
                if re.search(r"/visa-offers-and-perks/.+/\d+", href):
                    links.append((text, href))
        except Exception:
            links = re.findall(
                r'href=["\']([^"\']*visa-offers-and-perks/[^"\']+/\d+[^"\']*)["\'][^>]*>([^<]{3,200})',
                html,
                flags=re.I,
            )
            links = [(t, h) for h, t in links]

        out: List[Dict[str, Any]] = []
        seen = set()
        for title, href in links:
            if href.startswith("/"):
                u = urlparse(source)
                href = f"{u.scheme}://{u.netloc}{href}"
            if not href.startswith("https://"):
                continue
            try:
                assert_allowed_url(href.split("?")[0])
            except Exception:
                continue
            m = re.search(r"/visa-offers-and-perks/([^/]+)/(\d+)", href)
            if not m:
                continue
            slug, oid = m.group(1), m.group(2)
            if oid in seen:
                continue
            seen.add(oid)
            merchant = unquote(slug).replace("-", " ").strip().title()
            out.append(
                {
                    "sourceId": oid,
                    "title": title or merchant,
                    "merchantName": merchant,
                    "shortDescription": title or "",
                    "ApplyURL": href,
                    "OfficialSource": "Visa Offers & Perks",
                }
            )
        if not out:
            raise RuntimeError("No offer links found in rendered HTML (layout may have changed)")
        return out, fr.engine

    def _map_api_perk(self, perk: Dict[str, Any], *, origin: str, locale: str) -> Dict[str, Any]:
        md = perk.get("metaData") or {}
        custom = md.get("customAttributes") or {}
        source_id = str(perk.get("sourceId") or "")
        merchant = (perk.get("merchantName") or perk.get("title") or "").strip()
        title = (perk.get("title") or merchant or "").strip()
        desc = (perk.get("shortDescription") or "").strip()
        offer_copy = (custom.get("offerCopy") or "").strip()
        slug = re.sub(r"[^a-z0-9]+", "-", merchant.lower()).strip("-") or "offer"
        apply = f"{origin}/{locale}/visa-offers-and-perks/{slug}/{source_id}" if source_id else origin

        return {
            "sourceId": source_id,
            "title": title,
            "merchantName": merchant,
            "shortDescription": desc,
            "offerCopy": offer_copy,
            "startDate": perk.get("startDate"),
            "endDate": perk.get("endDate"),
            "featured": bool(perk.get("featured")),
            "image": perk.get("image") or "",
            "logo": custom.get("merchantLogo") or "",
            "ApplyURL": apply,
            "OfficialSource": "Visa Offers & Perks",
            "programName": custom.get("programName") or "",
            "_categories": md.get("categories") or [],
            "_cardProductTypes": md.get("cardProductTypes") or [],
            "_cardPaymentTypes": md.get("cardPaymentTypes") or [],
            "Bank": "Visa",
        }

    def _to_schema(
        self,
        raw: Dict[str, Any],
        *,
        source_url: str,
        meta_labels: Dict[str, Dict[str, str]],
        locale: str,
    ) -> Dict[str, Any]:
        cats = raw.get("_categories") or []
        cat_label = ""
        cat_map = meta_labels.get("categories") or DEFAULT_CATEGORY_LABELS
        for c in cats:
            if str(c) in cat_map:
                cat_label = cat_map[str(c)]
                break
        product_map = meta_labels.get("cardProductTypes") or {}
        products = raw.get("_cardProductTypes") or []
        eligible_parts = []
        for pid in products[:12]:
            eligible_parts.append(product_map.get(str(pid)) or f"Visa product #{pid}")
        eligible = ", ".join(eligible_parts)
        card_level = ""
        blob = (eligible + " " + str(raw.get("offerCopy") or "") + " " + str(raw.get("shortDescription") or "")).lower()
        for needle, level in CARD_LEVEL_HINTS:
            if needle.lower() in blob:
                card_level = level
                break
        title = raw.get("title") or raw.get("OfferTitle") or ""
        desc = raw.get("shortDescription") or raw.get("ShortDescription") or ""
        terms = raw.get("offerCopy") or raw.get("Terms") or ""
        merchant = raw.get("merchantName") or raw.get("Merchant") or title
        pid = raw.get("sourceId") or raw.get("PromotionID") or ""
        if pid:
            pid = f"visa-{pid}"

        return normalize_promotion(
            {
                "PromotionID": pid,
                "Bank": raw.get("Bank") or "Visa",
                "Card": raw.get("Card") or "",
                "CardLevel": card_level,
                "Merchant": merchant,
                "MerchantCategory": cat_label or raw.get("MerchantCategory") or "Other",
                "PromotionType": raw.get("PromotionType") or "Discount",
                "OfferTitle": title if title != merchant else (desc[:120] or title),
                "ShortDescription": desc,
                "EligibleCards": eligible,
                "StartDate": raw.get("startDate") or raw.get("StartDate"),
                "EndDate": raw.get("endDate") or raw.get("EndDate"),
                "ApplyURL": raw.get("ApplyURL") or source_url,
                "OfficialSource": raw.get("OfficialSource") or "Visa Offers & Perks",
                "Terms": terms[:4000],
                "Featured": raw.get("featured") or raw.get("Featured") or False,
                "Logo": raw.get("logo") or raw.get("Logo") or "",
                "Banner": raw.get("image") or raw.get("Banner") or "",
                "SourceURL": source_url,
                "Status": "Active",
                "Country": "Vietnam" if "vi_" in locale.lower() else "",
                "Priority": 80 if raw.get("featured") else 50,
            },
            source_url=source_url,
        )

    @staticmethod
    def _locale_from_path(path: str) -> Optional[str]:
        m = re.search(r"/([a-z]{2}_[a-z]{2})/", path or "", re.I)
        return m.group(1) if m else None

    @staticmethod
    def _labels_from_metadata(meta_def: List[Any]) -> Dict[str, Dict[str, str]]:
        out: Dict[str, Dict[str, str]] = {}
        for block in meta_def or []:
            if not isinstance(block, dict):
                continue
            name = block.get("name")
            md = block.get("metaData") or {}
            if name and isinstance(md, dict):
                out[str(name)] = {str(k): str(v) for k, v in md.items()}
        return out

