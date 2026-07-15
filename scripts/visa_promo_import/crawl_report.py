"""Crawl report for Import from URL — listing vs detail vs import integrity."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ListingCard:
    """One promotion card discovered on the listing page."""

    detail_url: str
    source_id: str = ""
    merchant: str = ""
    title: str = ""
    slug: str = ""


@dataclass
class CrawlReport:
    source_url: str = ""
    engine: str = ""
    parser: str = "visa_offers_perks"
    status: str = "ok"  # ok | failed | partial

    listing_promotions_found: int = 0
    detail_pages_visited: int = 0
    successfully_parsed: int = 0
    failed_urls: List[str] = field(default_factory=list)
    missing_promotions: List[str] = field(default_factory=list)
    duplicates_removed: int = 0
    import_summary: str = ""

    listing_cards: List[Dict[str, Any]] = field(default_factory=list)
    parsed_merchants: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Integrity flags
    count_mismatch: bool = False
    starbucks_on_listing: bool = False
    starbucks_imported: bool = False
    starbucks_check_failed: bool = False

    def log(self, message: str) -> None:
        msg = (message or "").strip()
        if not msg:
            return
        self.steps.append(msg)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source_url": self.source_url,
            "engine": self.engine,
            "parser": self.parser,
            "status": self.status,
            "listing_promotions_found": self.listing_promotions_found,
            "detail_pages_visited": self.detail_pages_visited,
            "successfully_parsed": self.successfully_parsed,
            "failed_urls": list(self.failed_urls),
            "missing_promotions": list(self.missing_promotions),
            "duplicates_removed": self.duplicates_removed,
            "import_summary": self.import_summary,
            "listing_cards": list(self.listing_cards),
            "parsed_merchants": list(self.parsed_merchants),
            "steps": list(self.steps),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "count_mismatch": self.count_mismatch,
            "starbucks_on_listing": self.starbucks_on_listing,
            "starbucks_imported": self.starbucks_imported,
            "starbucks_check_failed": self.starbucks_check_failed,
        }

    def finalize(
        self,
        *,
        listing_count: int,
        visited_count: int,
        parsed_count: int,
        duplicates_removed: int = 0,
        listing_labels: Optional[List[str]] = None,
        parsed_labels: Optional[List[str]] = None,
    ) -> "CrawlReport":
        """Compare counts and run dynamic Starbucks presence check (no hardcoding of import)."""
        self.listing_promotions_found = listing_count
        self.detail_pages_visited = visited_count
        self.successfully_parsed = parsed_count
        self.duplicates_removed = duplicates_removed

        listing_labels = listing_labels or [
            str(c.get("merchant") or c.get("title") or c.get("detail_url") or "")
            for c in self.listing_cards
        ]
        parsed_labels = parsed_labels or list(self.parsed_merchants)

        # Missing = on listing but not successfully parsed (by source id / label)
        listing_ids = {
            str(c.get("source_id") or "").strip()
            for c in self.listing_cards
            if c.get("source_id")
        }
        parsed_ids = {
            str(x).replace("visa-", "").strip()
            for x in (self.as_dict().get("_parsed_ids") or [])
        }
        # Prefer ID-based missing detection when available
        missing: List[str] = []
        if listing_ids and hasattr(self, "_parsed_source_ids"):
            missing_ids = listing_ids - set(self._parsed_source_ids)  # type: ignore[attr-defined]
            for c in self.listing_cards:
                sid = str(c.get("source_id") or "")
                if sid in missing_ids:
                    missing.append(
                        f"{c.get('merchant') or c.get('title') or sid} → {c.get('detail_url')}"
                    )
        else:
            # Fallback: label set comparison (case-insensitive)
            parsed_set = {p.strip().lower() for p in parsed_labels if p and p.strip()}
            for lab in listing_labels:
                if lab and lab.strip().lower() not in parsed_set:
                    # avoid flagging if merchant is substring of a parsed title
                    low = lab.strip().lower()
                    if not any(low in p or p in low for p in parsed_set):
                        missing.append(lab)

        # Also count-based mismatch
        if listing_count != visited_count or listing_count != parsed_count or visited_count != parsed_count:
            self.count_mismatch = True
            if listing_count > parsed_count and not missing:
                missing.append(
                    f"count gap: listing={listing_count} visited={visited_count} parsed={parsed_count}"
                )

        self.missing_promotions = missing

        # Dynamic Starbucks check: only if listing text/url contains starbucks
        listing_blob = " ".join(
            [
                " ".join(str(c.get(k) or "") for k in ("merchant", "title", "detail_url", "slug"))
                for c in self.listing_cards
            ]
            + listing_labels
        ).lower()
        self.starbucks_on_listing = "starbucks" in listing_blob
        parsed_blob = " ".join(parsed_labels).lower()
        self.starbucks_imported = "starbucks" in parsed_blob
        if self.starbucks_on_listing and not self.starbucks_imported:
            self.starbucks_check_failed = True
            self.errors.append(
                "CRAWL FAILED: listing contains Starbucks but imported dataset does not."
            )
            if not any("starbucks" in m.lower() for m in self.missing_promotions):
                self.missing_promotions.append("Starbucks (present on listing, missing after parse)")

        if self.starbucks_check_failed:
            self.status = "failed"
        elif not parsed_count:
            self.status = "failed"
        elif self.count_mismatch or self.failed_urls or self.missing_promotions:
            self.status = "partial"
        else:
            self.status = "ok"

        self.import_summary = (
            f"listing={listing_count} visited={visited_count} parsed={parsed_count} "
            f"failed_urls={len(self.failed_urls)} missing={len(self.missing_promotions)} "
            f"dupes_removed={duplicates_removed} status={self.status}"
        )
        self.log(f"Crawl report finalized: {self.import_summary}")
        return self


def format_report_text(report: CrawlReport) -> str:
    d = report.as_dict()
    lines = [
        "=== Visa Promo Crawl Report ===",
        f"Status: {d['status']}",
        f"Source: {d['source_url']}",
        f"Engine: {d['engine']} · Parser: {d['parser']}",
        f"Listing promotions found: {d['listing_promotions_found']}",
        f"Detail pages visited: {d['detail_pages_visited']}",
        f"Successfully parsed: {d['successfully_parsed']}",
        f"Duplicates removed: {d['duplicates_removed']}",
        f"Failed URLs ({len(d['failed_urls'])}):",
    ]
    for u in d["failed_urls"][:50]:
        lines.append(f"  - {u}")
    lines.append(f"Missing promotions ({len(d['missing_promotions'])}):")
    for m in d["missing_promotions"][:50]:
        lines.append(f"  - {m}")
    lines.append(f"Starbucks on listing: {d['starbucks_on_listing']}")
    lines.append(f"Starbucks imported: {d['starbucks_imported']}")
    lines.append(f"Starbucks check failed: {d['starbucks_check_failed']}")
    lines.append(f"Import summary: {d['import_summary']}")
    if d["errors"]:
        lines.append("Errors:")
        for e in d["errors"]:
            lines.append(f"  - {e}")
    if d["warnings"]:
        lines.append("Warnings:")
        for w in d["warnings"][:20]:
            lines.append(f"  - {w}")
    lines.append("Steps:")
    for s in d["steps"][-40:]:
        lines.append(f"  · {s}")
    return "\n".join(lines) + "\n"
