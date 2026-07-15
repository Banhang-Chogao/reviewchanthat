"""Unit tests for visa_promo_import (no network)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.visa_promo_import.allowlist import is_allowed_url  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
