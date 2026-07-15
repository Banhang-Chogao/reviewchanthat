"""Base parser contract for official promotion pages."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse


@dataclass
class ParseContext:
    source_url: str
    prefer_browser: bool = False
    skip_expired: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    def query(self) -> Dict[str, List[str]]:
        return parse_qs(urlparse(self.source_url).query)


@dataclass
class ParsedBatch:
    promotions: List[Dict[str, Any]]
    source_url: str
    parser: str
    engine: str = ""
    warnings: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


class BasePromotionParser(ABC):
    name: str = "base"

    @classmethod
    @abstractmethod
    def supports(cls, url: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, ctx: ParseContext) -> ParsedBatch:
        raise NotImplementedError
