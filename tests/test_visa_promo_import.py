"""Unit tests for visa_promo_import (no network)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.visa_promo_import.allowlist import is_allowed_url  # noqa: E402
from scripts.visa_promo_import.crawl_report import CrawlReport  # noqa: E402
from scripts.visa_promo_import.normalize import dedupe_promotions, normalize_promotion  # noqa: E402
from scripts.visa_promo_import.pipeline import merge_promotions  # noqa: E402
from scripts.visa_promo_import.parsers.visa_offers_perks import VisaOffersPerksParser  # noqa: E402


class AllowlistTests(unittest.TestCase):
    def test_visa_ok(self):
        self.assertTrue(
            is_allowed_url(
                "https://www.visa.com.vn/vi_vn/visa-offers-and-perks/?cardProduct=65&paymentType=9"
            )
        )

    def test_http_rejected(self):
        self.assertFalse(is_allowed_url("http://www.visa.com.vn/vi_vn/visa-offers-and-perks/"))

    def test_unrelated_rejected(self):
        self.assertFalse(is_allowed_url("https://evil.example.com/promo"))


class NormalizeTests(unittest.TestCase):
    def test_percent_and_dates(self):
        p = normalize_promotion(
            {
                "Merchant": "  Dusit Thani ",
                "OfferTitle": "Giảm 10% giá phòng",
                "ShortDescription": "Ưu đãi spa",
                "startDate": 1784125800000,
                "endDate": 1814365740000,
            },
            source_url="https://www.visa.com.vn/vi_vn/visa-offers-and-perks/",
        )
        self.assertEqual(p["Merchant"], "Dusit Thani")
        self.assertEqual(p["DiscountType"], "Percent")
        self.assertEqual(p["DiscountValue"], 10.0)
        self.assertRegex(p["StartDate"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertTrue(p["PromotionID"])

    def test_dedupe(self):
        a = normalize_promotion({"Merchant": "A", "OfferTitle": "X", "EndDate": "2026-12-01"})
        b = normalize_promotion({"Merchant": "A", "OfferTitle": "X", "EndDate": "2026-12-01"})
        self.assertEqual(len(dedupe_promotions([a, b])), 1)

    def test_generates_promotion_id_if_missing(self):
        p = normalize_promotion({"Merchant": "X", "OfferTitle": "Y"})
        self.assertTrue(p["PromotionID"])


class MergeTests(unittest.TestCase):
    def test_update_existing(self):
        existing = [
            normalize_promotion(
                {
                    "PromotionID": "visa-1",
                    "Merchant": "Old",
                    "OfferTitle": "Old title",
                    "EndDate": "2026-12-01",
                }
            )
        ]
        incoming = [
            normalize_promotion(
                {
                    "PromotionID": "visa-1",
                    "Merchant": "New",
                    "OfferTitle": "New title",
                    "EndDate": "2026-12-01",
                }
            )
        ]
        merged, report = merge_promotions(existing, incoming, mode="update")
        self.assertEqual(report.updated, 1)
        self.assertEqual(merged[0]["Merchant"], "New")


class ParserSupportTests(unittest.TestCase):
    def test_supports_visa_offers(self):
        self.assertTrue(
            VisaOffersPerksParser.supports(
                "https://www.visa.com.vn/vi_vn/visa-offers-and-perks/?cardProduct=65"
            )
        )
        self.assertFalse(VisaOffersPerksParser.supports("https://www.hsbc.com.vn/offers/"))


class CrawlReportTests(unittest.TestCase):
    def test_starbucks_dynamic_fail(self):
        report = CrawlReport(source_url="https://www.visa.com.vn/vi_vn/visa-offers-and-perks/")
        report.listing_cards = [
            {
                "detail_url": "https://www.visa.com.vn/vi_vn/visa-offers-and-perks/starbucks/177994",
                "source_id": "177994",
                "merchant": "Starbucks",
                "title": "Starbucks",
                "slug": "starbucks",
            },
            {
                "detail_url": "https://www.visa.com.vn/vi_vn/visa-offers-and-perks/cgv/1",
                "source_id": "1",
                "merchant": "CGV",
                "title": "CGV",
                "slug": "cgv",
            },
        ]
        report._parsed_source_ids = {"1"}  # type: ignore[attr-defined]
        report.finalize(
            listing_count=2,
            visited_count=2,
            parsed_count=1,
            parsed_labels=["CGV"],
        )
        self.assertTrue(report.starbucks_on_listing)
        self.assertFalse(report.starbucks_imported)
        self.assertTrue(report.starbucks_check_failed)
        self.assertEqual(report.status, "failed")

    def test_ok_when_counts_match(self):
        report = CrawlReport(source_url="https://www.visa.com.vn/x")
        report.listing_cards = [
            {
                "detail_url": "https://www.visa.com.vn/vi_vn/visa-offers-and-perks/cgv/1",
                "source_id": "1",
                "merchant": "CGV",
                "title": "CGV",
                "slug": "cgv",
            }
        ]
        report._parsed_source_ids = {"1"}  # type: ignore[attr-defined]
        report.finalize(listing_count=1, visited_count=1, parsed_count=1, parsed_labels=["CGV"])
        self.assertEqual(report.status, "ok")
        self.assertFalse(report.starbucks_check_failed)

    def test_parse_detail_fields_from_api_shape(self):
        parser = VisaOffersPerksParser()
        from scripts.visa_promo_import.fetcher import ListingLink

        link = ListingLink(
            detail_url="https://www.visa.com.vn/vi_vn/visa-offers-and-perks/starbucks/177994",
            source_id="177994",
            slug="starbucks",
            merchant="Starbucks",
            title="Starbucks",
        )
        api = {
            "offerId": "177994",
            "offerTitle": "",
            "offerShortDescription": {"text": "Visa x Starbucks - Khơi nguồn cảm hứng"},
            "merchantList": [{"merchant": "Starbucks", "merchantImages": []}],
            "cardProductList": [{"key": 65, "value": "Visa Signature"}],
            "cardPaymentTypeList": [{"key": 9, "value": "Tín dụng"}],
            "categorySubcategoryList": [{"key": 94, "value": "Ẩm thực"}],
            "redemptionCountries": [{"key": 240, "value": "Vietnam"}],
            "offerCopy": {"text": "Miễn phí upsize khi thanh toán ví di động. Tối thiểu 120.000đ"},
            "promotionFromDateTime": "Mar 30, 2026 17:00 GMT",
            "promotionToDateTime": "Sep 30, 2026 17:00 GMT",
            "validityFromDateTime": "Mar 30, 2026 17:00 GMT",
            "validityToDateTime": "Sep 30, 2026 17:00 GMT",
        }
        promo = parser._parse_detail_to_schema(
            link=link,
            api_raw=api,
            page_text="",
            images=[],
            source_url="https://www.visa.com.vn/vi_vn/visa-offers-and-perks/?cardProduct=65&paymentType=9",
            locale="vi_vn",
        )
        self.assertEqual(promo["Merchant"], "Starbucks")
        self.assertIn("Starbucks", promo["OfferTitle"] + promo["ShortDescription"])
        self.assertEqual(promo["PromotionID"], "visa-177994")
        self.assertEqual(promo["Country"], "Vietnam")
        self.assertTrue(promo["ApplyURL"].endswith("/starbucks/177994") or "177994" in promo["ApplyURL"])
        self.assertEqual(promo["StartDate"], "2026-03-30")
        self.assertEqual(promo["EndDate"], "2026-09-30")


if __name__ == "__main__":
    unittest.main()
