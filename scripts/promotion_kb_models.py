#!/usr/bin/env python3
"""
Normalized Promotion Knowledge Base models
Bank → Source → Merchant → Offer → Promotion

Local-only data (see .gitignore). Compatible with the Credit Card Dashboard
client schema (version 3 knowledgeBase payload).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import re
import uuid


OFFICIAL_HOST_SUFFIXES = (
    "hsbc.com.vn",
    "hsbc.com",
    "visa.com",
    "visa.com.vn",
    "mastercard.com",
    "mastercard.com.vn",
    "homeandaway.hsbc.com",
)

DEFAULT_SOURCES = [
    "HSBC Privilege Club",
    "Visa Offers",
    "Mastercard Priceless",
    "home&Away",
    "Bank Official Offers",
]

DEFAULT_OFFER_TYPES = [
    "Cashback",
    "Discount",
    "Installment",
    "Voucher",
    "Gift",
    "Miles",
    "Reward Point",
    "Fee Waiver",
    "Welcome Gift",
]

DEFAULT_MERCHANTS = [
    "Starbucks",
    "Shopee",
    "Grab",
    "Booking.com",
    "Agoda",
    "CGV",
    "Highlands Coffee",
]


def _id(prefix: str = "kb") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "item"


def is_https_official_url(url: str, extra_host_suffixes: Optional[List[str]] = None) -> bool:
    """Accept only https:// URLs on allow-listed official host suffixes."""
    if not url or not isinstance(url, str):
        return False
    u = url.strip()
    if not u.lower().startswith("https://"):
        return False
    # strip path
    try:
        from urllib.parse import urlparse

        host = (urlparse(u).hostname or "").lower()
    except Exception:
        return False
    if not host:
        return False
    suffixes = list(OFFICIAL_HOST_SUFFIXES)
    if extra_host_suffixes:
        suffixes.extend(extra_host_suffixes)
    for suf in suffixes:
        suf = suf.lower().lstrip(".")
        if host == suf or host.endswith("." + suf):
            return True
    return False


@dataclass
class Bank:
    id: str
    name: str
    slug: str = ""

    def __post_init__(self) -> None:
        if not self.slug:
            self.slug = _slug(self.name)


@dataclass
class PromotionSource:
    id: str
    bank_id: str
    name: str
    slug: str = ""

    def __post_init__(self) -> None:
        if not self.slug:
            self.slug = _slug(self.name)


@dataclass
class Merchant:
    id: str
    name: str
    domain: str = ""
    category: str = ""
    slug: str = ""

    def __post_init__(self) -> None:
        if not self.slug:
            self.slug = _slug(self.name)


@dataclass
class Offer:
    """Offer type node (Cashback / Discount / Installment / …)."""

    id: str
    type: str
    name: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.type


@dataclass
class Promotion:
    id: str
    promotion_id: str
    title: str
    description: str = ""
    category: str = ""
    merchant_id: str = ""
    source_id: str = ""
    bank_id: str = ""
    cards: List[str] = field(default_factory=list)
    start_date: str = ""
    end_date: str = ""
    status: str = "Active"
    priority: int = 50
    featured: bool = False
    minimum_spend: float = 0
    cashback_cap: float = 0
    installment_months: int = 0
    promo_code: str = ""
    terms: str = ""
    official_url: str = ""
    discount_type: str = "Percent"
    discount_value: float = 0
    offer_id: str = ""
    # denormalized labels for Excel / UI convenience
    bank: str = ""
    source: str = ""
    merchant: str = ""
    offer_type: str = ""
    created_at: str = ""
    updated_at: str = ""

    def is_expired(self, today: Optional[date] = None) -> bool:
        if (self.status or "").lower() == "expired":
            return True
        if not self.end_date:
            return False
        try:
            end = datetime.strptime(self.end_date[:10], "%Y-%m-%d").date()
        except ValueError:
            return False
        return end < (today or date.today())

    def to_flat(self) -> Dict[str, Any]:
        """Client-compatible flat promotion record."""
        return {
            "id": self.id,
            "promotionId": self.promotion_id,
            "bank": self.bank,
            "bankId": self.bank_id,
            "source": self.source,
            "sourceId": self.source_id,
            "merchant": self.merchant,
            "merchantId": self.merchant_id,
            "offerType": self.offer_type or self.discount_type,
            "offerId": self.offer_id,
            "promotionType": self.offer_type or "Cashback",
            "card": ", ".join(self.cards) if self.cards else "",
            "cards": list(self.cards),
            "offerTitle": self.title,
            "shortDescription": self.description,
            "category": self.category,
            "discountType": self.discount_type,
            "discountValue": self.discount_value,
            "cashbackCap": self.cashback_cap,
            "minimumSpend": self.minimum_spend,
            "installmentMonths": self.installment_months,
            "startDate": self.start_date,
            "endDate": self.end_date,
            "promoCode": self.promo_code,
            "applyLink": self.official_url,
            "officialUrl": self.official_url,
            "terms": self.terms,
            "priority": self.priority,
            "featured": self.featured,
            "status": "Expired" if self.is_expired() else self.status,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


@dataclass
class PromotionKnowledgeBase:
    version: int = 3
    banks: List[Bank] = field(default_factory=list)
    sources: List[PromotionSource] = field(default_factory=list)
    merchants: List[Merchant] = field(default_factory=list)
    offers: List[Offer] = field(default_factory=list)
    promotions: List[Promotion] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "banks": [asdict(b) for b in self.banks],
            "sources": [asdict(s) for s in self.sources],
            "merchants": [asdict(m) for m in self.merchants],
            "offers": [asdict(o) for o in self.offers],
            "promotions": [asdict(p) for p in self.promotions],
        }

    def flatten(self) -> List[Dict[str, Any]]:
        return [p.to_flat() for p in self.promotions]

    def ensure_seed(self) -> None:
        if not self.banks:
            self.banks.append(Bank(id=_id("bank"), name="HSBC"))
        bank = self.banks[0]
        if not self.sources:
            for name in DEFAULT_SOURCES:
                self.sources.append(
                    PromotionSource(id=_id("src"), bank_id=bank.id, name=name)
                )
        if not self.offers:
            for t in DEFAULT_OFFER_TYPES:
                self.offers.append(Offer(id=_id("offer"), type=t))
        if not self.merchants:
            for name in DEFAULT_MERCHANTS:
                self.merchants.append(Merchant(id=_id("merch"), name=name))

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "PromotionKnowledgeBase":
        if not data:
            kb = cls()
            kb.ensure_seed()
            return kb
        kb = cls(version=int(data.get("version") or 3))
        for b in data.get("banks") or []:
            kb.banks.append(Bank(**{k: b[k] for k in ("id", "name", "slug") if k in b}))
        for s in data.get("sources") or []:
            kb.sources.append(
                PromotionSource(
                    id=s.get("id") or _id("src"),
                    bank_id=s.get("bank_id") or s.get("bankId") or "",
                    name=s.get("name") or "",
                    slug=s.get("slug") or "",
                )
            )
        for m in data.get("merchants") or []:
            kb.merchants.append(
                Merchant(
                    id=m.get("id") or _id("merch"),
                    name=m.get("name") or "",
                    domain=m.get("domain") or "",
                    category=m.get("category") or "",
                    slug=m.get("slug") or "",
                )
            )
        for o in data.get("offers") or []:
            kb.offers.append(
                Offer(
                    id=o.get("id") or _id("offer"),
                    type=o.get("type") or o.get("name") or "Cashback",
                    name=o.get("name") or "",
                )
            )
        for p in data.get("promotions") or []:
            kb.promotions.append(
                Promotion(
                    id=p.get("id") or _id("promo"),
                    promotion_id=p.get("promotion_id") or p.get("promotionId") or "",
                    title=p.get("title") or p.get("offerTitle") or "",
                    description=p.get("description") or p.get("shortDescription") or "",
                    category=p.get("category") or "",
                    merchant_id=p.get("merchant_id") or p.get("merchantId") or "",
                    source_id=p.get("source_id") or p.get("sourceId") or "",
                    bank_id=p.get("bank_id") or p.get("bankId") or "",
                    cards=list(p.get("cards") or ([p["card"]] if p.get("card") else [])),
                    start_date=p.get("start_date") or p.get("startDate") or "",
                    end_date=p.get("end_date") or p.get("endDate") or "",
                    status=p.get("status") or "Active",
                    priority=int(p.get("priority") or 0),
                    featured=bool(p.get("featured")),
                    minimum_spend=float(p.get("minimum_spend") or p.get("minimumSpend") or 0),
                    cashback_cap=float(p.get("cashback_cap") or p.get("cashbackCap") or 0),
                    installment_months=int(
                        p.get("installment_months") or p.get("installmentMonths") or 0
                    ),
                    promo_code=p.get("promo_code") or p.get("promoCode") or "",
                    terms=p.get("terms") or "",
                    official_url=p.get("official_url")
                    or p.get("officialUrl")
                    or p.get("applyLink")
                    or "",
                    discount_type=p.get("discount_type") or p.get("discountType") or "Percent",
                    discount_value=float(p.get("discount_value") or p.get("discountValue") or 0),
                    offer_id=p.get("offer_id") or p.get("offerId") or "",
                    bank=p.get("bank") or "",
                    source=p.get("source") or "",
                    merchant=p.get("merchant") or "",
                    offer_type=p.get("offer_type")
                    or p.get("offerType")
                    or p.get("promotionType")
                    or "",
                    created_at=p.get("created_at") or p.get("createdAt") or "",
                    updated_at=p.get("updated_at") or p.get("updatedAt") or "",
                )
            )
        kb.ensure_seed()
        return kb

    @classmethod
    def from_flat_list(cls, flat: List[Dict[str, Any]]) -> "PromotionKnowledgeBase":
        """Migrate legacy flat promotions[] into normalized KB."""
        kb = cls()
        kb.ensure_seed()
        bank_by_name: Dict[str, Bank] = {b.name.lower(): b for b in kb.banks}
        src_by_key: Dict[str, PromotionSource] = {}
        merch_by_name: Dict[str, Merchant] = {m.name.lower(): m for m in kb.merchants}
        offer_by_type: Dict[str, Offer] = {o.type.lower(): o for o in kb.offers}

        for row in flat or []:
            bank_name = (row.get("bank") or "HSBC").strip() or "HSBC"
            if bank_name.lower() not in bank_by_name:
                b = Bank(id=_id("bank"), name=bank_name)
                kb.banks.append(b)
                bank_by_name[bank_name.lower()] = b
            bank = bank_by_name[bank_name.lower()]

            source_name = (
                row.get("source")
                or row.get("promotionGroup")
                or "Bank Official Offers"
            ).strip()
            sk = f"{bank.id}:{source_name.lower()}"
            if sk not in src_by_key:
                s = PromotionSource(id=_id("src"), bank_id=bank.id, name=source_name)
                kb.sources.append(s)
                src_by_key[sk] = s
            source = src_by_key[sk]

            merch_name = (row.get("merchant") or "General").strip() or "General"
            if merch_name.lower() not in merch_by_name:
                m = Merchant(id=_id("merch"), name=merch_name)
                kb.merchants.append(m)
                merch_by_name[merch_name.lower()] = m
            merchant = merch_by_name[merch_name.lower()]

            otype = (
                row.get("offerType")
                or row.get("promotionType")
                or row.get("offer_type")
                or "Cashback"
            ).strip()
            if otype.lower() not in offer_by_type:
                o = Offer(id=_id("offer"), type=otype)
                kb.offers.append(o)
                offer_by_type[otype.lower()] = o
            offer = offer_by_type[otype.lower()]

            cards = row.get("cards")
            if not cards:
                c = row.get("card") or ""
                cards = [x.strip() for x in str(c).split(",") if x.strip()]

            url = (
                row.get("officialUrl")
                or row.get("official_url")
                or row.get("applyLink")
                or ""
            ).strip()

            promo = Promotion(
                id=row.get("id") or _id("promo"),
                promotion_id=row.get("promotionId") or row.get("promotion_id") or _id("PID"),
                title=row.get("offerTitle") or row.get("title") or "",
                description=row.get("shortDescription") or row.get("description") or "",
                category=row.get("category") or "",
                merchant_id=merchant.id,
                source_id=source.id,
                bank_id=bank.id,
                cards=cards,
                start_date=row.get("startDate") or row.get("start_date") or "",
                end_date=row.get("endDate") or row.get("end_date") or "",
                status=row.get("status") or "Active",
                priority=int(row.get("priority") or 0),
                featured=bool(row.get("featured")),
                minimum_spend=float(row.get("minimumSpend") or row.get("minimum_spend") or 0),
                cashback_cap=float(row.get("cashbackCap") or row.get("cashback_cap") or 0),
                installment_months=int(
                    row.get("installmentMonths") or row.get("installment_months") or 0
                ),
                promo_code=row.get("promoCode") or row.get("promo_code") or "",
                terms=row.get("terms") or "",
                official_url=url,
                discount_type=row.get("discountType") or row.get("discount_type") or "Percent",
                discount_value=float(row.get("discountValue") or row.get("discount_value") or 0),
                offer_id=offer.id,
                bank=bank.name,
                source=source.name,
                merchant=merchant.name,
                offer_type=offer.type,
                created_at=row.get("createdAt") or row.get("created_at") or "",
                updated_at=row.get("updatedAt") or row.get("updated_at") or "",
            )
            kb.promotions.append(promo)
        return kb


EXCEL_HEADERS = [
    "Promotion ID",
    "Bank",
    "Promotion Source",
    "Merchant",
    "Offer Type",
    "Card(s)",
    "Title",
    "Description",
    "Category",
    "Discount Type",
    "Discount Value",
    "Cashback Cap",
    "Minimum Spend",
    "Installment Months",
    "Start Date",
    "End Date",
    "Promo Code",
    "Official URL",
    "Terms",
    "Priority",
    "Featured",
    "Status",
]


if __name__ == "__main__":
    kb = PromotionKnowledgeBase()
    kb.ensure_seed()
    print("banks", len(kb.banks), "sources", len(kb.sources), "offers", len(kb.offers))
    print("URL ok", is_https_official_url("https://www.hsbc.com.vn/credit-cards/"))
    print("URL bad", is_https_official_url("http://example.com"))
