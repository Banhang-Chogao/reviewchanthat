"""Parser registry — pick a source-specific parser without hardcoding UI selectors."""

from __future__ import annotations

from typing import List, Optional, Type

from .base import BasePromotionParser, ParseContext, ParsedBatch
from .generic_html import GenericHtmlParser
from .visa_offers_perks import VisaOffersPerksParser

# Order matters: first match wins.
PARSERS: List[Type[BasePromotionParser]] = [
    VisaOffersPerksParser,
    # Future: MastercardPricelessParser, JcbParser, AmexParser, BankIssuerParser
    GenericHtmlParser,
]


def pick_parser(url: str) -> BasePromotionParser:
    for cls in PARSERS:
        if cls.supports(url):
            return cls()
    return GenericHtmlParser()


def parse_url(url: str, **kwargs) -> ParsedBatch:
    parser = pick_parser(url)
    ctx = ParseContext(source_url=url, **kwargs)
    return parser.parse(ctx)
