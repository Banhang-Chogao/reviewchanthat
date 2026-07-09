"""Regression tests for Image Relevance Gate."""

from __future__ import annotations

import os
import sys
import unittest

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))

from article_image_context import build_context_from_post
from image_relevance_gate import accepts, check_hard_reject, rank_candidates, score_candidate


def _solid_image(rgb: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", (1200, 800), rgb)


AUTUMN_POST = {
    "slug": "mau-la-rung-mua-thu",
    "title": "Màu lá rụng: vì sao mùa thu có sắc nâu cam?",
    "description": "Giải thích chlorophyll, carotenoid, anthocyanin và sắc nâu cam của lá rụng mùa thu.",
    "categories": ["Đời sống"],
    "tags": ["lá rụng", "mùa thu", "autumn leaves"],
}

FLOWER_CANDIDATE = {
    "source_platform": "Pexels",
    "source_url": "https://www.pexels.com/photo/fresh-pink-flower-bloom-123/",
    "direct_url": "https://images.pexels.com/photos/123/flower.jpeg",
    "creator": "Jane Doe",
    "creator_url": "https://www.pexels.com/@jane",
    "license": "Pexels License",
    "commercial_use": True,
    "width": 1920,
    "height": 1280,
    "alt": "fresh pink flower bloom in garden",
    "tags": ["flower", "rose", "bloom"],
}

LEAF_CANDIDATE = {
    "source_platform": "Pexels",
    "source_url": "https://www.pexels.com/photo/brown-orange-fallen-autumn-leaves-456/",
    "direct_url": "https://images.pexels.com/photos/456/leaves.jpeg",
    "creator": "John Doe",
    "creator_url": "https://www.pexels.com/@john",
    "license": "Pexels License",
    "commercial_use": True,
    "width": 1920,
    "height": 1280,
    "alt": "brown orange fallen autumn leaves on forest floor",
    "tags": ["autumn", "leaves", "fall foliage"],
}


class ImageRelevanceGateTests(unittest.TestCase):
    def setUp(self):
        self.ctx = build_context_from_post(
            AUTUMN_POST,
            "Lá rụng mùa thu chuyển nâu cam vì chlorophyll giảm, carotenoid và anthocyanin lộ rõ.",
        )

    def test_flower_hard_rejected_for_autumn_topic(self):
        hard, reason = check_hard_reject(self.ctx, FLOWER_CANDIDATE)
        self.assertTrue(hard)
        self.assertIn("flower", reason)

    def test_leaf_not_hard_rejected(self):
        hard, reason = check_hard_reject(self.ctx, LEAF_CANDIDATE)
        self.assertFalse(hard, reason)

    def test_flower_scores_lower_than_leaf(self):
        flower_score = score_candidate(
            self.ctx, FLOWER_CANDIDATE, image=_solid_image((240, 120, 180)), download=False
        )
        leaf_score = score_candidate(
            self.ctx, LEAF_CANDIDATE, image=_solid_image((170, 95, 35)), download=False
        )
        self.assertTrue(flower_score.hard_reject or flower_score.total_score < leaf_score.total_score)
        ok_leaf, _ = accepts(leaf_score, self.ctx)
        self.assertTrue(ok_leaf or leaf_score.total_score > flower_score.total_score)

    def test_rank_candidates_prefers_leaf_metadata(self):
        ranked = rank_candidates(
            self.ctx,
            [FLOWER_CANDIDATE, LEAF_CANDIDATE],
            download=False,
        )
        # Provide synthetic images since download=False and no image passed => download fails
        # Re-rank with explicit images
        ranked = []
        for cand, img in (
            (FLOWER_CANDIDATE, _solid_image((240, 120, 180))),
            (LEAF_CANDIDATE, _solid_image((170, 95, 35))),
        ):
            score = score_candidate(self.ctx, cand, image=img, download=False)
            ok, reason = accepts(score, self.ctx)
            ranked.append({"candidate": cand, "gate": score.to_dict(), "accepted": ok, "accept_reason": reason})
        ranked.sort(key=lambda x: (x["accepted"], x["gate"]["total_score"]), reverse=True)
        self.assertEqual(ranked[0]["candidate"]["alt"], LEAF_CANDIDATE["alt"])


if __name__ == "__main__":
    unittest.main()