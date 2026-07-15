"""End-to-end import pipeline: validate → fetch → parse → normalize → report."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

from .allowlist import assert_allowed_url, is_allowed_url
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
        }


def import_from_url(
    url: str,
    *,
    existing: Optional[List[Dict[str, Any]]] = None,
    skip_expired: bool = False,
    prefer_browser: bool = False,
) -> ImportReport:
    """
    Crawl + extract + normalize promotions from one official URL.

    Does not write storage — caller merges into Visa Promo dataset.
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

    normalized = [normalize_promotion(p, source_url=report.source_url) for p in batch.promotions]
    normalized = dedupe_promotions(normalized)

    existing_ids = {
        str(p.get("PromotionID") or "").lower()
        for p in existing
        if p.get("PromotionID")
    }
    existing_fp = {
        _fp(p)
        for p in existing
    }

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
