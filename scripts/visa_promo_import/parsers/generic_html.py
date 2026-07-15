"""
Generic semantic HTML parser for future official issuer pages.

Prefers structured data (JSON-LD, OpenGraph, microdata) over CSS selectors.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

from ..allowlist import assert_allowed_url
from ..fetcher import fetch_rendered_html, http_get
from ..normalize import normalize_promotion
from .base import BasePromotionParser, ParseContext, ParsedBatch


class GenericHtmlParser(BasePromotionParser):
    name = "generic_html"

    @classmethod
    def supports(cls, url: str) -> bool:
        # Catch-all for allowlisted pages not handled by specialized parsers.
        try:
            assert_allowed_url(url)
            return True
        except Exception:
            return False

    def parse(self, ctx: ParseContext) -> ParsedBatch:
        source = assert_allowed_url(ctx.source_url)
        warnings: List[str] = []
        engine = "httpx"
        html = ""

        try:
            if ctx.prefer_browser:
                fr = fetch_rendered_html(source)
                html, engine = fr.body, fr.engine
            else:
                try:
                    fr = http_get(source, referer=source)
                    html, engine = fr.body, fr.engine
                    # Heuristic: SPA shell → use browser
                    if len(html) < 4000 and ("app-root" in html or "id=\"root\"" in html):
                        warnings.append("Detected SPA shell; switching to browser renderer.")
                        fr = fetch_rendered_html(source)
                        html, engine = fr.body, fr.engine
                except Exception as e:  # noqa: BLE001
                    warnings.append(f"HTTP fetch failed ({e}); trying browser.")
                    fr = fetch_rendered_html(source)
                    html, engine = fr.body, fr.engine
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"Broken page / fetch failed for {source}: {e}") from e

        items = self._extract_semantic(html, source)
        if not items:
            items = self._extract_headings(html, source)
        if not items:
            raise RuntimeError(
                "No promotions found via semantic extraction. "
                "Add a specialized parser for this layout."
            )

        promotions = []
        for raw in items:
            p = normalize_promotion(raw, source_url=source)
            if not p.get("OfferTitle"):
                continue
            if ctx.skip_expired and p.get("Status") == "Expired":
                continue
            promotions.append(p)

        return ParsedBatch(
            promotions=promotions,
            source_url=source,
            parser=self.name,
            engine=engine,
            warnings=warnings,
            meta={"count": len(promotions)},
        )

    def _extract_semantic(self, html: str, source: str) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        try:
            from bs4 import BeautifulSoup  # type: ignore

            soup = BeautifulSoup(html, "lxml")
            for tag in soup(["script", "style", "noscript"]):
                # Keep application/ld+json
                if tag.name == "script" and tag.get("type") == "application/ld+json":
                    continue
                if tag.name == "script":
                    tag.decompose()
                elif tag.name in ("style", "noscript"):
                    tag.decompose()

            for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
                try:
                    data = json.loads(script.string or "")
                except Exception:
                    continue
                out.extend(self._from_jsonld(data, source))

            # OpenGraph single offer pages
            og_title = soup.find("meta", property="og:title")
            og_desc = soup.find("meta", property="og:description")
            if og_title and og_title.get("content") and not out:
                out.append(
                    {
                        "OfferTitle": og_title["content"],
                        "ShortDescription": (og_desc.get("content") if og_desc else "") or "",
                        "Merchant": og_title["content"][:80],
                        "ApplyURL": source,
                        "OfficialSource": urlparse(source).hostname or "",
                    }
                )
        except Exception:
            return out
        return out

    def _from_jsonld(self, data: Any, source: str) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []

        def walk(node: Any) -> None:
            if isinstance(node, list):
                for x in node:
                    walk(x)
                return
            if not isinstance(node, dict):
                return
            t = node.get("@type") or node.get("type") or ""
            types = t if isinstance(t, list) else [t]
            types_l = [str(x).lower() for x in types]
            if any(x in ("offer", "product", "event") for x in types_l):
                title = node.get("name") or node.get("title") or ""
                desc = node.get("description") or ""
                url = node.get("url") or source
                if isinstance(url, str) and url.startswith("/"):
                    url = urljoin(source, url)
                items.append(
                    {
                        "OfferTitle": title,
                        "ShortDescription": desc,
                        "Merchant": title,
                        "ApplyURL": url if isinstance(url, str) else source,
                        "StartDate": node.get("validFrom") or node.get("startDate"),
                        "EndDate": node.get("validThrough") or node.get("endDate"),
                        "OfficialSource": urlparse(source).hostname or "",
                    }
                )
            for v in node.values():
                if isinstance(v, (dict, list)):
                    walk(v)

        walk(data)
        return items

    def _extract_headings(self, html: str, source: str) -> List[Dict[str, Any]]:
        """Last-resort: h2/h3 blocks that look like offers (percent / discount language)."""
        try:
            from bs4 import BeautifulSoup  # type: ignore

            soup = BeautifulSoup(html, "lxml")
            for tag in soup(["script", "style", "noscript", "iframe"]):
                tag.decompose()
            out: List[Dict[str, Any]] = []
            for h in soup.find_all(re.compile(r"^h[2-3]$")):
                text = h.get_text(" ", strip=True)
                if len(text) < 8:
                    continue
                if not re.search(r"(%|giảm|ưu đãi|discount|cashback|off\b)", text, re.I):
                    continue
                sibling = h.find_next(["p", "div"])
                desc = sibling.get_text(" ", strip=True)[:400] if sibling else ""
                out.append(
                    {
                        "OfferTitle": text[:200],
                        "ShortDescription": desc,
                        "Merchant": text.split("—")[0][:80],
                        "ApplyURL": source,
                        "OfficialSource": urlparse(source).hostname or "",
                    }
                )
            return out[:100]
        except Exception:
            return []
