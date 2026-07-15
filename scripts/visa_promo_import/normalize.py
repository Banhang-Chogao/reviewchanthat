"""Normalize raw extracted promotions into the Visa Promo Center schema."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

CATEGORY_MAP = {
    "du lịch": "Travel",
    "du lich": "Travel",
    "travel": "Travel",
    "hotel": "Hotel",
    "khách sạn": "Hotel",
    "khach san": "Hotel",
    "dining": "Dining",
    "ẩm thực": "Dining",
    "am thuc": "Dining",
    "fnb": "Dining",
    "coffee": "Coffee",
    "shopping": "Shopping",
    "mua sắm": "Shopping",
    "entertainment": "Entertainment",
    "giải trí": "Entertainment",
    "electronics": "Electronics",
    "lifestyle": "Lifestyle",
    "phong cách sống": "Lifestyle",
    "other": "Other",
}

TYPE_MAP = {
    "cashback": "Cashback",
    "discount": "Discount",
    "installment": "Installment",
    "voucher": "Voucher",
    "miles": "Miles",
    "gift": "Gift",
    "reward": "Gift",
    "offers": "Discount",
}


def _trim(v: Any) -> str:
    if v is None:
        return ""
    return re.sub(r"\s+", " ", str(v)).strip()


def _parse_money(v: Any) -> float:
    if isinstance(v, (int, float)):
        return float(v) if v == v else 0.0  # NaN guard
    s = _trim(v)
    if not s:
        return 0.0
    s = re.sub(r"[^\d\-.,]", "", s)
    if s.count(".") > 1:
        s = s.replace(".", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_percent(text: str) -> Optional[float]:
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", text or "")
    if not m:
        return None
    return float(m.group(1).replace(",", "."))


def _parse_date(v: Any) -> str:
    """Return YYYY-MM-DD or empty."""
    if v is None or v == "":
        return ""
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, (int, float)):
        # epoch ms or s
        n = float(v)
        if n > 1e12:
            n /= 1000.0
        try:
            return datetime.fromtimestamp(n, tz=timezone.utc).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return ""
    s = _trim(v)
    if not s:
        return ""
    # ISO-ish
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.match(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # assume dd/mm/yyyy for VN
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            try:
                return date(y, d, mo).isoformat()
            except ValueError:
                return ""
    return ""


def _norm_category(v: str) -> str:
    key = _trim(v).lower()
    if not key:
        return "Other"
    if key in CATEGORY_MAP:
        return CATEGORY_MAP[key]
    for k, mapped in CATEGORY_MAP.items():
        if k in key:
            return mapped
    # Title-case known English
    titled = _trim(v).title()
    allowed = {
        "Dining",
        "Travel",
        "Shopping",
        "Entertainment",
        "Coffee",
        "Hotel",
        "Electronics",
        "Lifestyle",
        "Other",
    }
    return titled if titled in allowed else "Other"


def _norm_type(v: str, title: str = "", desc: str = "") -> str:
    key = _trim(v).lower()
    if key in TYPE_MAP:
        return TYPE_MAP[key]
    blob = f"{title} {desc}".lower()
    if re.search(r"\b(trả góp|installment|0%)\b", blob):
        return "Installment"
    if re.search(r"\b(cashback|hoàn tiền)\b", blob):
        return "Cashback"
    if re.search(r"\b(voucher|phiếu|mã giảm)\b", blob):
        return "Voucher"
    if re.search(r"\b(dặm|miles)\b", blob):
        return "Miles"
    if re.search(r"\d+\s*%", blob) or re.search(r"giảm|discount|ưu đãi", blob):
        return "Discount"
    return "Discount"


def _norm_status(v: str, end_date: str) -> str:
    s = _trim(v) or "Active"
    today = date.today().isoformat()
    if end_date and end_date < today:
        return "Expired"
    allowed = {"Active", "Pending", "Verified", "Expired", "Draft"}
    titled = s.title() if s.lower() != "active" else "Active"
    return titled if titled in allowed else "Active"


def _infer_discount(title: str, desc: str) -> tuple[str, float]:
    blob = f"{title} {desc}"
    pct = _parse_percent(blob)
    if pct is not None:
        return "Percent", pct
    m = re.search(r"(\d[\d.,]*)\s*(?:₫|đ|vnd|vnđ)", blob, re.I)
    if m:
        return "Fixed", _parse_money(m.group(1))
    m = re.search(r"lên đến\s+(\d[\d.,]*)", blob, re.I)
    if m:
        return "Fixed", _parse_money(m.group(1))
    return "Other", 0.0


def empty_promotion() -> Dict[str, Any]:
    return {
        "id": "",
        "PromotionID": "",
        "Bank": "Visa",
        "Card": "",
        "CardLevel": "",
        "Merchant": "",
        "MerchantCategory": "Other",
        "PromotionType": "Discount",
        "OfferTitle": "",
        "ShortDescription": "",
        "DiscountType": "Percent",
        "DiscountValue": 0,
        "CashbackCap": 0,
        "MinimumSpend": 0,
        "InstallmentMonths": 0,
        "EligibleCards": "",
        "Country": "Vietnam",
        "City": "",
        "StartDate": "",
        "EndDate": "",
        "PromoCode": "",
        "ApplyURL": "",
        "OfficialSource": "",
        "Terms": "",
        "Priority": 50,
        "Featured": False,
        "Status": "Active",
        "Logo": "",
        "Banner": "",
        "UpdatedAt": "",
        "Verified": "Pending",
        "LastVerified": "",
        "VerifiedBy": "",
        "SourceURL": "",
    }


def normalize_promotion(raw: Dict[str, Any], *, source_url: str = "") -> Dict[str, Any]:
    base = empty_promotion()
    # Accept both schema keys and loose aliases
    aliases = {
        "promotionId": "PromotionID",
        "promotion_id": "PromotionID",
        "offerTitle": "OfferTitle",
        "offer_title": "OfferTitle",
        "shortDescription": "ShortDescription",
        "merchantCategory": "MerchantCategory",
        "promotionType": "PromotionType",
        "discountType": "DiscountType",
        "discountValue": "DiscountValue",
        "cashbackCap": "CashbackCap",
        "minimumSpend": "MinimumSpend",
        "installmentMonths": "InstallmentMonths",
        "eligibleCards": "EligibleCards",
        "promoCode": "PromoCode",
        "applyURL": "ApplyURL",
        "applyUrl": "ApplyURL",
        "officialSource": "OfficialSource",
        "sourceURL": "SourceURL",
        "sourceUrl": "SourceURL",
        "startDate": "StartDate",
        "endDate": "EndDate",
        "cardLevel": "CardLevel",
    }
    merged: Dict[str, Any] = {}
    for k, v in (raw or {}).items():
        key = aliases.get(k, k)
        merged[key] = v

    for k in base:
        if k in merged and merged[k] is not None:
            base[k] = merged[k]

    base["Bank"] = _trim(base.get("Bank")) or "Visa"
    base["Card"] = _trim(base.get("Card"))
    base["CardLevel"] = _trim(base.get("CardLevel"))
    base["Merchant"] = _trim(base.get("Merchant"))
    base["OfferTitle"] = _trim(base.get("OfferTitle"))
    base["ShortDescription"] = _trim(base.get("ShortDescription"))
    base["Terms"] = _trim(base.get("Terms"))
    base["PromoCode"] = _trim(base.get("PromoCode"))
    base["City"] = _trim(base.get("City"))
    base["Country"] = _trim(base.get("Country")) or "Vietnam"
    base["EligibleCards"] = _trim(base.get("EligibleCards"))
    base["ApplyURL"] = _trim(base.get("ApplyURL"))
    base["OfficialSource"] = _trim(base.get("OfficialSource")) or "Visa Offers & Perks"
    base["Logo"] = _trim(base.get("Logo"))
    base["Banner"] = _trim(base.get("Banner"))
    base["SourceURL"] = _trim(base.get("SourceURL")) or source_url

    if not base["Merchant"] and base["OfferTitle"]:
        base["Merchant"] = base["OfferTitle"].split("—")[0].split("-")[0].strip()[:80]

    base["MerchantCategory"] = _norm_category(str(base.get("MerchantCategory") or ""))
    base["PromotionType"] = _norm_type(
        str(base.get("PromotionType") or ""),
        base["OfferTitle"],
        base["ShortDescription"],
    )

    base["StartDate"] = _parse_date(base.get("StartDate"))
    base["EndDate"] = _parse_date(base.get("EndDate"))
    if not base["StartDate"]:
        base["StartDate"] = date.today().isoformat()

    dtype = _trim(base.get("DiscountType")) or "Percent"
    dval = base.get("DiscountValue")
    if not dval:
        inferred_type, inferred_val = _infer_discount(base["OfferTitle"], base["ShortDescription"])
        dtype = inferred_type
        dval = inferred_val
    base["DiscountType"] = dtype if dtype in ("Percent", "Fixed", "Other") else "Other"
    base["DiscountValue"] = float(dval or 0)
    base["CashbackCap"] = _parse_money(base.get("CashbackCap"))
    base["MinimumSpend"] = _parse_money(base.get("MinimumSpend"))
    try:
        base["InstallmentMonths"] = int(base.get("InstallmentMonths") or 0)
    except (TypeError, ValueError):
        base["InstallmentMonths"] = 0
    try:
        base["Priority"] = int(base.get("Priority") or 50)
    except (TypeError, ValueError):
        base["Priority"] = 50
    base["Featured"] = bool(base.get("Featured")) in (True,) or str(base.get("Featured")).lower() in (
        "1",
        "true",
        "yes",
        "y",
    )

    base["Status"] = _norm_status(str(base.get("Status") or ""), base["EndDate"])
    if not base["PromotionID"]:
        base["PromotionID"] = str(uuid.uuid4())
    if not base["id"]:
        base["id"] = str(uuid.uuid4())
    base["UpdatedAt"] = _trim(base.get("UpdatedAt")) or datetime.now(timezone.utc).isoformat()
    if not base.get("Verified"):
        base["Verified"] = "Pending"
    return base


def dedupe_promotions(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicates by PromotionID, then by merchant+title+end."""
    seen_id: set[str] = set()
    seen_fp: set[str] = set()
    out: List[Dict[str, Any]] = []
    for p in items:
        pid = _trim(p.get("PromotionID")).lower()
        if pid and pid in seen_id:
            continue
        fp = "|".join(
            [
                _trim(p.get("Merchant")).lower(),
                _trim(p.get("OfferTitle")).lower(),
                _trim(p.get("EndDate")),
                _trim(p.get("ApplyURL")).lower(),
            ]
        )
        if fp in seen_fp:
            continue
        if pid:
            seen_id.add(pid)
        seen_fp.add(fp)
        out.append(p)
    return out
