"""End-to-end import pipeline: validate → fetch → parse → normalize → report."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

from .allowlist import assert_allowed_url, is_allowed_url
from .crawl_report import CrawlReport, format_report_text
from .normalize import dedupe_promotions, normalize_promotion
from .parsers import parse_url


@dataclass
class ImportReport:
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    promotions: List[Dict[str, Any]] = field(default_factory=list)
    source_url: str = ""
    parser: str = ""
    engine: str = ""
    crawl_report: Optional[Dict[str, Any]] = None
    crawl_report_text: str = ""
    import_blocked: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            "imported": self.imported,
            "updated": self.updated,
            "skipped": self.skipped,
            "failures": self.failures,
            "warnings": self.warnings,
            "count": len(self.promotions),
            "source_url": self.source_url,
            "parser": self.parser,
            "engine": self.engine,
            "crawl_report": self.crawl_report,
            "crawl_report_text": self.crawl_report_text,
            "import_blocked": self.import_blocked,
        }


def import_from_url(
    url: str,
    *,
    existing: Optional[List[Dict[str, Any]]] = None,
    skip_expired: bool = False,
    prefer_browser: bool = True,
) -> ImportReport:
    """
    Crawl + extract + normalize promotions from one official URL.

    Prefer Playwright browser crawl (prefer_browser=True by default).
    Does not write storage — caller merges into Visa Promo dataset.

    Integrity: if crawl report status is failed (count mismatch / Starbucks
    on listing missing from import), promotions are not imported.
    """
    report = ImportReport(source_url=(url or "").strip())
    existing = existing or []

    if not report.source_url:
        report.failures.append("Missing URL")
        return report
    if not is_allowed_url(report.source_url):
        report.failures.append("Invalid or non-official URL domain")
        return report

    try:
        assert_allowed_url(report.source_url)
        batch = parse_url(
            report.source_url,
            skip_expired=skip_expired,
            prefer_browser=prefer_browser,
        )
    except Exception as exc:  # noqa: BLE001
        report.failures.append(str(exc))
        return report

    report.parser = batch.parser
    report.engine = batch.engine
    report.warnings.extend(batch.warnings or [])
    meta = batch.meta or {}
    report.crawl_report = meta.get("crawl_report")
    report.crawl_report_text = meta.get("crawl_report_text") or ""
    report.import_blocked = bool(meta.get("import_blocked"))

    if report.import_blocked:
        cr = report.crawl_report or {}
        report.failures.append(
            "Import blocked by crawl integrity check "
            f"(listing={cr.get('listing_promotions_found')} "
            f"visited={cr.get('detail_pages_visited')} "
            f"parsed={cr.get('successfully_parsed')} "
            f"missing={cr.get('missing_promotions')} "
            f"starbucks_failed={cr.get('starbucks_check_failed')})"
        )
        if not report.crawl_report_text and report.crawl_report:
            # best-effort text
            try:
                tmp = CrawlReport(source_url=report.source_url)
                for k, v in report.crawl_report.items():
                    if hasattr(tmp, k):
                        setattr(tmp, k, v)
                report.crawl_report_text = format_report_text(tmp)
            except Exception:
                pass
        report.promotions = []
        report.imported = 0
        return report

    before_dedupe = len(batch.promotions)
    normalized = [normalize_promotion(p, source_url=report.source_url) for p in batch.promotions]
    normalized = dedupe_promotions(normalized)
    deduped = before_dedupe - len(normalized)
    if deduped > 0:
        report.warnings.append(f"Removed {deduped} duplicates in batch")
        if report.crawl_report and isinstance(report.crawl_report, dict):
            report.crawl_report["duplicates_removed"] = (
                int(report.crawl_report.get("duplicates_removed") or 0) + deduped
            )

    # Surface count mismatch as warnings (do not silently drop context)
    if report.crawl_report and isinstance(report.crawl_report, dict):
        if report.crawl_report.get("count_mismatch") or report.crawl_report.get("missing_promotions"):
            missing = report.crawl_report.get("missing_promotions") or []
            report.warnings.append(
                "Crawl count mismatch — missing: " + (", ".join(missing[:12]) or "(see crawl report)")
            )
        if report.crawl_report.get("starbucks_check_failed"):
            report.import_blocked = True
            report.failures.append(
                "CRAWL FAILED: listing contains Starbucks but imported dataset does not."
            )
            report.promotions = []
            report.imported = 0
            return report

    existing_ids = {
        str(p.get("PromotionID") or "").lower()
        for p in existing
        if p.get("PromotionID")
    }
    existing_fp = {_fp(p) for p in existing}

    out: List[Dict[str, Any]] = []
    for p in normalized:
        if not p.get("OfferTitle"):
            report.skipped += 1
            report.failures.append(f"Missing title skipped: {p.get('Merchant') or '?'}")
            continue
        if skip_expired and p.get("Status") == "Expired":
            report.skipped += 1
            continue
        if p.get("EndDate") and p["EndDate"] < date.today().isoformat() and skip_expired:
            report.skipped += 1
            continue
        pid = str(p.get("PromotionID") or "").lower()
        if pid and pid in existing_ids:
            report.skipped += 1
            report.failures.append(f"Duplicate PromotionID: {p.get('PromotionID')}")
            continue
        if _fp(p) in existing_fp:
            report.skipped += 1
            report.failures.append(f"Duplicate offer: {p.get('Merchant')} / {p.get('OfferTitle')}")
            continue
        out.append(p)
        report.imported += 1

    report.promotions = out
    if not out and not report.failures:
        report.failures.append("No promotions extracted from page")

    # Final dynamic Starbucks verification against listing cards in crawl report
    if report.crawl_report and isinstance(report.crawl_report, dict):
        cards = report.crawl_report.get("listing_cards") or []
        listing_blob = " ".join(
            str(c.get("merchant") or "") + " " + str(c.get("detail_url") or "") for c in cards
        ).lower()
        if "starbucks" in listing_blob:
            imported_blob = " ".join(
                str(p.get("Merchant") or "") + " " + str(p.get("OfferTitle") or "") for p in out
            ).lower()
            # If nothing imported solely due to existing duplicates, don't fail Starbucks
            if "starbucks" not in imported_blob and report.imported > 0:
                # Only fail if Starbucks was not even in the normalized batch
                batch_blob = " ".join(
                    str(p.get("Merchant") or "") for p in normalized
                ).lower()
                if "starbucks" not in batch_blob:
                    report.import_blocked = True
                    report.failures.append(
                        "CRAWL FAILED: listing contains Starbucks but imported dataset does not."
                    )
                    report.promotions = []
                    report.imported = 0

    return report


def _fp(p: Dict[str, Any]) -> str:
    return "|".join(
        [
            str(p.get("Merchant") or "").strip().lower(),
            str(p.get("OfferTitle") or "").strip().lower(),
            str(p.get("EndDate") or "").strip(),
        ]
    )


def merge_promotions(
    existing: List[Dict[str, Any]],
    incoming: List[Dict[str, Any]],
    mode: str = "append",
) -> tuple[List[Dict[str, Any]], ImportReport]:
    """
    Merge strategies: append | replace | update
    """
    mode = (mode or "append").lower()
    report = ImportReport()
    if mode == "replace":
        report.imported = len(incoming)
        report.promotions = list(incoming)
        return list(incoming), report

    if mode == "update":
        by_id = {str(p.get("PromotionID") or "").lower(): i for i, p in enumerate(existing)}
        by_fp = {_fp(p): i for i, p in enumerate(existing)}
        result = list(existing)
        for p in incoming:
            pid = str(p.get("PromotionID") or "").lower()
            idx = by_id.get(pid) if pid else None
            if idx is None:
                idx = by_fp.get(_fp(p))
            if idx is not None:
                keep_id = result[idx].get("id")
                merged = dict(result[idx])
                merged.update(p)
                if keep_id:
                    merged["id"] = keep_id
                result[idx] = merged
                report.updated += 1
            else:
                result.append(p)
                report.imported += 1
        report.promotions = result
        return result, report

    # append
    result = list(existing)
    existing_ids = {str(p.get("PromotionID") or "").lower() for p in existing}
    existing_fps = {_fp(p) for p in existing}
    for p in incoming:
        pid = str(p.get("PromotionID") or "").lower()
        if pid and pid in existing_ids:
            report.skipped += 1
            continue
        if _fp(p) in existing_fps:
            report.skipped += 1
            continue
        result.append(p)
        report.imported += 1
        if pid:
            existing_ids.add(pid)
        existing_fps.add(_fp(p))
    report.promotions = result
    return result, report
