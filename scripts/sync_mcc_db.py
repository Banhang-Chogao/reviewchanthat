#!/usr/bin/env python3
"""
MCC + Vietnam BIN intelligence sync pipeline.

Pipeline: Fetch → Validate → Normalize → Diff → Update → Report

Sources:
  - MCC: public greggles/mcc-codes (compiled MCC lists aligned with ISO 18245 ranges)
  - BIN: curated Vietnam IIN/BIN from Napas public listings + community sources

Never fabricates MCC/BIN values. Unknown fields stay "Unknown".
Does not overwrite higher-quality verificationStatus with lower-quality remote data.

Usage:
  python3 scripts/sync_mcc_db.py
  python3 scripts/sync_mcc_db.py --mcc-only
  python3 scripts/sync_mcc_db.py --bin-only
  python3 scripts/sync_mcc_db.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "mcc-db.json"
STATIC_PATH = ROOT / "static" / "data" / "mcc-db.json"
MCC_SOURCE_URL = "https://raw.githubusercontent.com/greggles/mcc-codes/main/mcc_codes.json"
MCC_SOURCE_LABEL = (
    "https://github.com/greggles/mcc-codes (compiled public MCC lists; ISO 18245 ranges)"
)
TZ_HCM = timezone(timedelta(hours=7))

# High-frequency Vietnamese display names (curated). Others fall back to English.
VI_NAMES: dict[str, str] = {
    "0742": "Dịch vụ thú y",
    "1520": "Nhà thầu xây dựng nhà ở",
    "4111": "Vận tải hành khách địa phương / ngoại ô",
    "4112": "Tàu hỏa hành khách",
    "4121": "Taxi / limousine",
    "4131": "Xe buýt",
    "4215": "Dịch vụ chuyển phát nhanh (courier)",
    "4411": "Du thuyền / cruise",
    "4511": "Hãng hàng không / vận tải hàng không",
    "4582": "Sân bay / nhà ga / đường băng",
    "4722": "Đại lý du lịch / tour",
    "4784": "Phí cầu đường / đường cao tốc",
    "4812": "Thiết bị / bán điện thoại",
    "4814": "Dịch vụ viễn thông (gọi)",
    "4816": "Mạng máy tính / thông tin",
    "4899": "Truyền hình cáp / trả tiền",
    "4900": "Điện / gas / nước / vệ sinh",
    "5045": "Máy tính / phần mềm / ngoại vi",
    "5122": "Thuốc / dược phẩm",
    "5200": "Cửa hàng vật liệu xây dựng nhà",
    "5211": "Gỗ / vật liệu xây dựng",
    "5251": "Cửa hàng phần cứng",
    "5300": "Cửa hàng bán sỉ",
    "5309": "Duty free",
    "5310": "Cửa hàng giảm giá",
    "5311": "Cửa hàng bách hóa",
    "5331": "Cửa hàng tiện lợi",
    "5399": "Hàng hóa tổng hợp khác",
    "5411": "Siêu thị / tạp hóa",
    "5422": "Thịt đông lạnh / tủ đông",
    "5441": "Kẹo / hạt / trái quả khô",
    "5451": "Cửa hàng sữa",
    "5462": "Tiệm bánh",
    "5499": "Cửa hàng thực phẩm khác",
    "5511": "Đại lý xe mới / cũ",
    "5533": "Phụ tùng / phụ kiện xe",
    "5541": "Trạm xăng (có / không dịch vụ phụ)",
    "5542": "Trạm xăng tự phục vụ",
    "5611": "Quần áo nam",
    "5621": "Quần áo nữ",
    "5641": "Quần áo / phụ kiện trẻ em",
    "5651": "Quần áo gia đình",
    "5661": "Cửa hàng giày",
    "5691": "Cửa hàng quần áo nam / nữ",
    "5699": "Phụ kiện quần áo khác",
    "5712": "Nội thất / trang trí nhà",
    "5722": "Thiết bị gia dụng",
    "5732": "Điện tử",
    "5734": "Cửa hàng phần mềm máy tính",
    "5735": "Cửa hàng đĩa nhạc",
    "5811": "Caterer / suất ăn",
    "5812": "Nhà hàng / ăn uống",
    "5813": "Bar / quán rượu / club / nightlife",
    "5814": "Fast food",
    "5912": "Nhà thuốc",
    "5921": "Rượu / bia / vang",
    "5940": "Cửa hàng xe đạp",
    "5941": "Đồ thể thao",
    "5942": "Nhà sách",
    "5944": "Đồng hồ / trang sức / bạc",
    "5945": "Đồ chơi / sở thích / game",
    "5947": "Quà tặng / thiệp / kỷ niệm",
    "5977": "Mỹ phẩm",
    "5992": "Tiệm hoa",
    "5995": "Thú cưng / đồ thú cưng",
    "5999": "Cửa hàng chuyên biệt khác",
    "6010": "Ngân hàng — rút tiền mặt thủ công",
    "6011": "ATM",
    "6012": "Tổ chức tài chính — hàng hóa / dịch vụ",
    "6211": "Chứng khoán / broker / dealer",
    "6300": "Bảo hiểm — sales / underwriting / premiums",
    "7011": "Khách sạn / motel / resort",
    "7012": "Timeshares",
    "7210": "Giặt ủi / vệ sinh / tẩy",
    "7230": "Salon tóc / làm đẹp",
    "7298": "Health / beauty spas",
    "7299": "Dịch vụ cá nhân khác",
    "7311": "Quảng cáo",
    "7372": "Computer programming / data processing",
    "7399": "Business services not elsewhere classified",
    "7512": "Automobile rental agency",
    "7523": "Bãi giữ xe / garage",
    "7538": "Automotive service shops",
    "7542": "Rửa xe",
    "7832": "Rạp chiếu phim",
    "7841": "Cho thuê băng đĩa / video",
    "7922": "Theatrical producers / ticket agencies",
    "7995": "Betting / casino / lottery / gambling",
    "7996": "Công viên giải trí / carnival",
    "7997": "Membership clubs / sports / recreation",
    "7999": "Recreation services not elsewhere classified",
    "8011": "Bác sĩ",
    "8021": "Nha sĩ / chỉnh nha",
    "8043": "Kính mắt / opticians",
    "8062": "Bệnh viện",
    "8071": "Medical / dental laboratories",
    "8099": "Medical services / health practitioners",
    "8111": "Dịch vụ pháp lý / luật sư",
    "8211": "Trường tiểu học / trung học",
    "8220": "Đại học / cao đẳng",
    "8299": "Schools / educational services",
    "8351": "Dịch vụ trông trẻ",
    "8398": "Tổ chức từ thiện / xã hội",
    "8734": "Testing laboratories (non-medical)",
    "8911": "Architectural / engineering / surveying",
    "8931": "Accounting / auditing / bookkeeping",
    "8999": "Professional services not elsewhere classified",
    "9211": "Court costs / alimony / child support",
    "9311": "Thuế / tax payments",
    "9399": "Government services not elsewhere classified",
    "9402": "Bưu chính — government only",
}

TYPICAL: dict[str, list[str]] = {
    "5411": ["VinMart", "Co.opmart", "Big C", "AEON", "Lotte Mart", "Go!"],
    "5812": ["The Coffee House", "Highlands", "Phở 24", "Pizza 4P's", "Gogi House"],
    "5814": ["KFC", "McDonald's", "Lotteria", "Jollibee", "Popeyes", "Domino's"],
    "5813": ["Bia Craft", "Pub", "Lounge"],
    "5541": ["Petrolimex", "Shell", "Caltex", "PVOIL"],
    "5542": ["Petrolimex", "Shell"],
    "4121": ["GrabCar", "Be", "Xanh SM", "taxi truyền thống"],
    "4111": ["Metro HCMC", "bus Hanoi", "xe buýt"],
    "4511": ["Vietnam Airlines", "Vietjet", "Bamboo Airways"],
    "4722": ["Klook", "Traveloka", "Booking.com agency"],
    "7011": ["Vinpearl", "Mường Thanh", "Accor", "IHG"],
    "5732": ["FPT Shop", "CellphoneS", "Điện Máy Xanh"],
    "5311": ["Takashimaya", "AEON Mall", "Vincom"],
    "5912": ["Pharmacity", "Long Châu", "An Khang"],
    "6011": ["ATM Vietcombank", "Techcombank", "MB", "VPBank"],
    "4900": ["EVN", "Sawaco", "cấp nước"],
    "4814": ["Viettel", "Mobifone", "Vinaphone"],
    "7832": ["CGV", "Lotte Cinema", "Galaxy"],
    "8062": ["BV Chợ Rẫy", "BV Việt Đức", "Vinmec"],
    "8011": ["phòng khám tư", "bác sĩ"],
    "5942": ["Fahasa", "Nhã Nam", "bookstores"],
    "5995": ["Pet Mart", "pet shops"],
    "7230": ["salon tóc", "nail spa"],
    "7298": ["spa", "wellness"],
    "7523": ["bãi giữ xe", "parking"],
    "7538": ["garage ô tô", "sửa xe"],
}

KEYWORDS_EXTRA: dict[str, list[str]] = {
    "5411": ["grocery", "supermarket", "siêu thị", "tạp hóa"],
    "5812": ["restaurant", "dining", "nhà hàng", "ăn uống"],
    "5814": ["fast food", "đồ ăn nhanh"],
    "5813": ["bar", "nightlife", "quán bar"],
    "5541": ["gas", "fuel", "xăng"],
    "4121": ["taxi", "grab", "ride-hail"],
    "4511": ["airline", "flight", "vé máy bay"],
    "7011": ["hotel", "khách sạn"],
    "5912": ["pharmacy", "nhà thuốc"],
    "5732": ["electronics", "điện tử"],
}

CASHBACK_RULES: list[tuple[Any, str, str]] = [
    ([5811, 5812, 5813, 5814], "Dining", "Ăn uống"),
    ([5411, 5422, 5441, 5451, 5462, 5499], "Grocery", "Siêu thị / Tạp hóa"),
    (range(3000, 3300), "Travel", "Du lịch / Hàng không"),
    (range(3500, 4000), "Travel", "Du lịch / Khách sạn"),
    ([7011, 7012], "Travel", "Du lịch / Lưu trú"),
    ([4111, 4112, 4121, 4131, 4411, 4511, 4582, 4722, 4784, 4789], "Travel", "Du lịch / Di chuyển"),
    ([5541, 5542, 5983], "Gas", "Xăng dầu"),
    ([5912, 5122, 8011, 8021, 8031, 8041, 8042, 8043, 8049, 8050, 8062, 8071, 8099], "Healthcare", "Y tế / Dược"),
    ([5311, 5310, 5300, 5331, 5399, 5200, 5211, 5251, 5261], "Shopping", "Mua sắm"),
    ([5651, 5611, 5621, 5631, 5641, 5661, 5681, 5691, 5699], "Shopping", "Thời trang"),
    ([5732, 5734, 5045, 4816, 7372], "Electronics / Digital", "Điện tử / Số"),
    ([4899, 4814, 4812, 4900], "Utilities / Telecom", "Tiện ích / Viễn thông"),
    ([5995, 742], "Pets", "Thú cưng"),
    ([7995, 7996, 7997, 7998, 7999, 7832, 7841, 7922, 7929, 7932, 7933, 7941], "Entertainment", "Giải trí"),
    ([8211, 8220, 8241, 8244, 8249, 8299, 8351], "Education", "Giáo dục"),
    ([6010, 6011, 6012, 6051, 6211], "Financial", "Tài chính"),
]

# Curated Vietnam BINs — public Napas 6-digit + community international BIN notes.
# Do not invent. Prefer Unknown over guesswork.
VN_BIN_SEED: list[dict[str, Any]] = [
    {"bin": "970436", "bank": "Vietcombank", "bankCode": "VCB", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings / bank product docs", "sourceUrl": "https://www.vietcombank.com.vn/", "notes": "BIN thẻ ghi nợ nội địa Vietcombank (6 số)."},
    {"bin": "428310", "bank": "Vietcombank", "bankCode": "VCB", "cardBrand": "Visa", "network": "Visa", "cardType": "Credit", "product": "Visa Credit", "level": "Unknown", "consumerBusiness": "Consumer", "active": True, "source": "Public BIN community lists cross-checked with issuer brand", "sourceUrl": "https://www.vietcombank.com.vn/", "notes": "BIN Visa credit cộng đồng ghi nhận cho VCB — verify với sao kê thực tế."},
    {"bin": "461140", "bank": "Vietcombank", "bankCode": "VCB", "cardBrand": "Visa", "network": "Visa", "cardType": "Debit", "product": "Visa Debit", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Public BIN listings", "sourceUrl": "https://www.vietcombank.com.vn/", "notes": ""},
    {"bin": "970407", "bank": "Techcombank", "bankCode": "TCB", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://techcombank.com/", "notes": ""},
    {"bin": "422149", "bank": "Techcombank", "bankCode": "TCB", "cardBrand": "Visa", "network": "Visa", "cardType": "Credit", "product": "Visa Credit", "level": "Unknown", "consumerBusiness": "Consumer", "active": True, "source": "Public BIN community lists", "sourceUrl": "https://techcombank.com/", "notes": ""},
    {"bin": "472689", "bank": "Techcombank", "bankCode": "TCB", "cardBrand": "Visa", "network": "Visa", "cardType": "Debit", "product": "Visa Debit", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Public BIN listings", "sourceUrl": "https://techcombank.com/", "notes": ""},
    {"bin": "970422", "bank": "MB Bank", "bankCode": "MB", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.mbbank.com.vn/", "notes": ""},
    {"bin": "356480", "bank": "MB Bank", "bankCode": "MB", "cardBrand": "JCB", "network": "JCB", "cardType": "Credit", "product": "JCB Credit", "level": "Unknown", "consumerBusiness": "Consumer", "active": True, "source": "Public BIN / issuer product pages", "sourceUrl": "https://www.mbbank.com.vn/", "notes": ""},
    {"bin": "970432", "bank": "VPBank", "bankCode": "VPB", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.vpbank.com.vn/", "notes": ""},
    {"bin": "469655", "bank": "VPBank", "bankCode": "VPB", "cardBrand": "Visa", "network": "Visa", "cardType": "Credit", "product": "Visa Credit", "level": "Unknown", "consumerBusiness": "Consumer", "active": True, "source": "Public BIN community lists", "sourceUrl": "https://www.vpbank.com.vn/", "notes": ""},
    {"bin": "970418", "bank": "BIDV", "bankCode": "BIDV", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.bidv.com.vn/", "notes": ""},
    {"bin": "418230", "bank": "BIDV", "bankCode": "BIDV", "cardBrand": "Visa", "network": "Visa", "cardType": "Credit", "product": "Visa Credit", "level": "Unknown", "consumerBusiness": "Consumer", "active": True, "source": "Public BIN community lists", "sourceUrl": "https://www.bidv.com.vn/", "notes": ""},
    {"bin": "970405", "bank": "Agribank", "bankCode": "AGR", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.agribank.com.vn/", "notes": ""},
    {"bin": "970416", "bank": "ACB", "bankCode": "ACB", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.acb.com.vn/", "notes": ""},
    {"bin": "356105", "bank": "ACB", "bankCode": "ACB", "cardBrand": "JCB", "network": "JCB", "cardType": "Credit", "product": "JCB Credit", "level": "Unknown", "consumerBusiness": "Consumer", "active": True, "source": "Public BIN / issuer product pages", "sourceUrl": "https://www.acb.com.vn/", "notes": ""},
    {"bin": "970403", "bank": "Sacombank", "bankCode": "STB", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.sacombank.com.vn/", "notes": ""},
    {"bin": "436437", "bank": "Sacombank", "bankCode": "STB", "cardBrand": "Visa", "network": "Visa", "cardType": "Credit", "product": "Visa Credit", "level": "Unknown", "consumerBusiness": "Consumer", "active": True, "source": "Public BIN community lists", "sourceUrl": "https://www.sacombank.com.vn/", "notes": ""},
    {"bin": "970423", "bank": "TPBank", "bankCode": "TPB", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://tpb.vn/", "notes": ""},
    {"bin": "459944", "bank": "TPBank", "bankCode": "TPB", "cardBrand": "Visa", "network": "Visa", "cardType": "Credit", "product": "Visa Credit", "level": "Unknown", "consumerBusiness": "Consumer", "active": True, "source": "Public BIN community lists", "sourceUrl": "https://tpb.vn/", "notes": ""},
    {"bin": "970441", "bank": "VIB", "bankCode": "VIB", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.vib.com.vn/", "notes": ""},
    {"bin": "356477", "bank": "VIB", "bankCode": "VIB", "cardBrand": "JCB", "network": "JCB", "cardType": "Credit", "product": "JCB Credit", "level": "Unknown", "consumerBusiness": "Consumer", "active": True, "source": "Issuer product pages / public BIN", "sourceUrl": "https://www.vib.com.vn/", "notes": ""},
    {"bin": "970443", "bank": "SHB", "bankCode": "SHB", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.shb.com.vn/", "notes": ""},
    {"bin": "970437", "bank": "HDBank", "bankCode": "HDB", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.hdbank.com.vn/", "notes": ""},
    {"bin": "970426", "bank": "MSB", "bankCode": "MSB", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.msb.com.vn/", "notes": ""},
    {"bin": "970448", "bank": "OCB", "bankCode": "OCB", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.ocb.com.vn/", "notes": ""},
    {"bin": "970440", "bank": "SeABank", "bankCode": "SSB", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.seabank.com.vn/", "notes": ""},
    {"bin": "970449", "bank": "LPBank", "bankCode": "LPB", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.lpbank.com.vn/", "notes": "Trước đây LienVietPostBank."},
    {"bin": "970431", "bank": "Eximbank", "bankCode": "EIB", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.eximbank.com.vn/", "notes": ""},
    {"bin": "452502", "bank": "HSBC Vietnam", "bankCode": "HSBC", "cardBrand": "Visa", "network": "Visa", "cardType": "Credit", "product": "Visa Credit", "level": "Unknown", "consumerBusiness": "Consumer", "active": True, "source": "Public BIN community lists / issuer brand", "sourceUrl": "https://www.hsbc.com.vn/", "notes": "BIN có thể khác theo sản phẩm; xác minh trên sao kê."},
    {"bin": "456364", "bank": "HSBC Vietnam", "bankCode": "HSBC", "cardBrand": "Visa", "network": "Visa", "cardType": "Credit", "product": "Visa Live+ / Cashback-class", "level": "Unknown", "consumerBusiness": "Consumer", "active": True, "source": "Public BIN community lists", "sourceUrl": "https://www.hsbc.com.vn/", "notes": ""},
    {"bin": "450823", "bank": "Standard Chartered Vietnam", "bankCode": "SCVN", "cardBrand": "Visa", "network": "Visa", "cardType": "Credit", "product": "Visa Credit", "level": "Unknown", "consumerBusiness": "Consumer", "active": True, "source": "Public BIN community lists", "sourceUrl": "https://www.sc.com/vn/", "notes": "Không nhầm với ngân hàng SCB nội địa cũ."},
    {"bin": "970424", "bank": "Shinhan Bank Vietnam", "bankCode": "SHBVN", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.shinhan.com.vn/", "notes": ""},
    {"bin": "970454", "bank": "Cake by VPBank", "bankCode": "CAKE", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit số", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas / digital bank product docs", "sourceUrl": "https://cake.vn/", "notes": "BIN digital bank — xác minh theo phiên bản thẻ."},
    {"bin": "970415", "bank": "Timo (BVBank)", "bankCode": "TIMO", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit số", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Public digital-bank BIN notes", "sourceUrl": "https://www.timo.vn/", "notes": "Một số nguồn cộng đồng cũng gắn 970415 cho issuer khác — cần đối chiếu thẻ thật."},
    {"bin": "970489", "bank": "VietinBank", "bankCode": "CTG", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.vietinbank.vn/", "notes": ""},
    {"bin": "413527", "bank": "VietinBank", "bankCode": "CTG", "cardBrand": "Visa", "network": "Visa", "cardType": "Credit", "product": "Visa Credit", "level": "Unknown", "consumerBusiness": "Consumer", "active": True, "source": "Public BIN community lists", "sourceUrl": "https://www.vietinbank.vn/", "notes": ""},
    {"bin": "970428", "bank": "Nam A Bank", "bankCode": "NAB", "cardBrand": "Napas", "network": "Napas", "cardType": "Debit", "product": "ATM / Debit nội địa", "level": "Classic", "consumerBusiness": "Consumer", "active": True, "source": "Napas domestic BIN public listings", "sourceUrl": "https://www.namabank.com.vn/", "notes": ""},
    {"bin": "552461", "bank": "Citibank Vietnam (legacy)", "bankCode": "CITI", "cardBrand": "Mastercard", "network": "Mastercard", "cardType": "Credit", "product": "Mastercard Credit", "level": "Unknown", "consumerBusiness": "Consumer", "active": False, "source": "Historical public BIN listings", "sourceUrl": "https://www.citibank.com.vn/", "notes": "Portfolio đã chuyển; giữ để tra cứu lịch sử."},
]

STATUS_RANK = {
    "verified": 3,
    "source-listed": 2,
    "community-sourced": 1,
    "needs-review": 0,
    "unknown": 0,
}


def now_hcm() -> str:
    return datetime.now(TZ_HCM).strftime("%Y-%m-%dT%H:%M:%S+07:00")


def industry_for(mcc: int) -> tuple[str, str]:
    if 1 <= mcc <= 1499:
        return "Agricultural Services", "Nông nghiệp / Dịch vụ nông nghiệp"
    if 1500 <= mcc <= 2999:
        return "Contracted Services", "Dịch vụ hợp đồng"
    if 3000 <= mcc <= 3299:
        return "Airlines", "Hãng hàng không"
    if 3300 <= mcc <= 3499:
        return "Car Rental", "Thuê xe"
    if 3500 <= mcc <= 3999:
        return "Lodging / Hotels", "Lưu trú / Khách sạn"
    if 4000 <= mcc <= 4799:
        return "Transportation", "Vận tải"
    if 4800 <= mcc <= 4999:
        return "Utilities", "Tiện ích"
    if 5000 <= mcc <= 5599:
        return "Retail Outlet", "Bán lẻ"
    if 5600 <= mcc <= 5699:
        return "Clothing", "Thời trang"
    if 5700 <= mcc <= 7299:
        return "Miscellaneous Shops", "Cửa hàng đa dạng"
    if 7300 <= mcc <= 7999:
        return "Business Services", "Dịch vụ doanh nghiệp"
    if 8000 <= mcc <= 8999:
        return "Professional Services / Health", "Dịch vụ chuyên môn / Y tế"
    if 9000 <= mcc <= 9999:
        return "Government / Other", "Chính phủ / Khác"
    return "Unknown", "Không xác định"


def cashback_for(mcc: int) -> tuple[str, str]:
    for rule, en, vi in CASHBACK_RULES:
        if isinstance(rule, range):
            if mcc in rule:
                return en, vi
        elif mcc in rule:
            return en, vi
    return "General", "Chung"


def parent_category(mcc: int, industry_en: str) -> str:
    cb, _ = cashback_for(mcc)
    if cb != "General":
        return cb
    return industry_en.split("/")[0].strip()


def fetch_json(url: str, timeout: int = 60) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "reviewchanthat-mcc-sync/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def validate_mcc_row(row: dict[str, Any]) -> str | None:
    code = str(row.get("mcc") or "").strip()
    if not code.isdigit() or not (1 <= len(code) <= 4):
        return "invalid mcc"
    name = (row.get("edited_description") or row.get("combined_description") or "").strip()
    if not name:
        return "missing description"
    return None


def normalize_mcc(row: dict[str, Any], verified: str) -> dict[str, Any]:
    code = str(row["mcc"]).zfill(4)
    n = int(code)
    name_en = (
        row.get("edited_description")
        or row.get("combined_description")
        or row.get("irs_description")
        or "Unknown"
    ).strip()
    ind_en, ind_vi = industry_for(n)
    cb_en, cb_vi = cashback_for(n)
    vi_exact = VI_NAMES.get(code, "Unknown")
    name_vi = name_en if vi_exact == "Unknown" else vi_exact
    keywords = [name_en.lower(), code]
    if vi_exact != "Unknown":
        keywords.append(vi_exact.lower())
    keywords.extend(KEYWORDS_EXTRA.get(code, []))
    typical = TYPICAL.get(code, [])
    status = "verified" if code in VI_NAMES or code in TYPICAL else "source-listed"
    return {
        "mcc": code,
        "name": name_en,
        "nameVi": name_vi,
        "nameViExact": vi_exact,
        "industry": ind_en,
        "industryVi": ind_vi,
        "parentCategory": parent_category(n, ind_en),
        "description": name_en,
        "typicalMerchants": typical,
        "cashbackCategory": cb_en,
        "cashbackCategoryVi": cb_vi,
        "visaCategory": ind_en,
        "mastercardCategory": ind_en,
        "scope": "Domestic / International",
        "keywords": sorted(set(keywords)),
        "relatedMccs": [],
        "notes": "",
        "verificationStatus": status,
        "lastVerified": verified,
        "source": MCC_SOURCE_LABEL,
        "sourceUrl": "https://github.com/greggles/mcc-codes",
    }


def attach_related(mccs: list[dict[str, Any]]) -> None:
    by_parent: dict[str, list[str]] = {}
    for m in mccs:
        by_parent.setdefault(m["parentCategory"], []).append(m["mcc"])
    for m in mccs:
        peers = [c for c in by_parent.get(m["parentCategory"], []) if c != m["mcc"]][:6]
        m["relatedMccs"] = peers


def normalize_bin(seed: dict[str, Any], verified: str) -> dict[str, Any]:
    bin_code = str(seed["bin"]).strip()
    if not bin_code.isdigit() or len(bin_code) not in (6, 8):
        raise ValueError(f"invalid BIN: {bin_code}")
    src = seed.get("source") or "Unknown"
    if "community" in src.lower() or src.startswith("Public"):
        status = "community-sourced"
    elif "Historical" in src:
        status = "needs-review"
    else:
        status = "source-listed"
    return {
        "bin": bin_code,
        "binLength": len(bin_code),
        "bank": seed.get("bank") or "Unknown",
        "bankCode": seed.get("bankCode") or "Unknown",
        "cardBrand": seed.get("cardBrand") or "Unknown",
        "network": seed.get("network") or "Unknown",
        "cardType": seed.get("cardType") or "Unknown",
        "product": seed.get("product") or "Unknown",
        "level": seed.get("level") or "Unknown",
        "consumerBusiness": seed.get("consumerBusiness") or "Unknown",
        "issuerCountry": "VN",
        "currency": "VND",
        "active": bool(seed.get("active", True)),
        "cashbackCompatibility": "Unknown",
        "typicalPromotions": "Unknown",
        "notes": seed.get("notes") or "",
        "verificationStatus": status,
        "lastVerified": verified,
        "source": src,
        "sourceUrl": seed.get("sourceUrl") or "",
    }


def load_existing() -> dict[str, Any] | None:
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if STATIC_PATH.exists():
        return json.loads(STATIC_PATH.read_text(encoding="utf-8"))
    return None


def merge_mccs(
    incoming: list[dict[str, Any]], existing: list[dict[str, Any]] | None
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Prefer higher verificationStatus; never downgrade quality."""
    stats = {"added": 0, "updated": 0, "kept": 0, "skipped_low_quality": 0}
    by_code = {m["mcc"]: m for m in (existing or [])}
    for m in incoming:
        old = by_code.get(m["mcc"])
        if not old:
            by_code[m["mcc"]] = m
            stats["added"] += 1
            continue
        old_rank = STATUS_RANK.get(old.get("verificationStatus", "unknown"), 0)
        new_rank = STATUS_RANK.get(m.get("verificationStatus", "unknown"), 0)
        if new_rank < old_rank:
            # Keep better record; refresh lastVerified only if same source
            stats["skipped_low_quality"] += 1
            stats["kept"] += 1
            continue
        # Preserve curated typical merchants / VI name if remote has empty
        merged = dict(m)
        if old.get("typicalMerchants") and not merged.get("typicalMerchants"):
            merged["typicalMerchants"] = old["typicalMerchants"]
        if old.get("nameViExact") not in (None, "", "Unknown") and merged.get("nameViExact") == "Unknown":
            merged["nameViExact"] = old["nameViExact"]
            merged["nameVi"] = old.get("nameVi") or merged["nameVi"]
        by_code[m["mcc"]] = merged
        stats["updated"] += 1
    out = sorted(by_code.values(), key=lambda x: x["mcc"])
    attach_related(out)
    return out, stats


def merge_bins(
    incoming: list[dict[str, Any]], existing: list[dict[str, Any]] | None
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    stats = {"added": 0, "updated": 0, "kept": 0, "skipped_low_quality": 0}
    # Key = bin + bank (same BIN can appear for different products rarely)
    def key(b: dict[str, Any]) -> str:
        return f"{b['bin']}|{b.get('bank', '')}"

    by_key = {key(b): b for b in (existing or [])}
    for b in incoming:
        k = key(b)
        old = by_key.get(k)
        if not old:
            by_key[k] = b
            stats["added"] += 1
            continue
        old_rank = STATUS_RANK.get(old.get("verificationStatus", "unknown"), 0)
        new_rank = STATUS_RANK.get(b.get("verificationStatus", "unknown"), 0)
        if new_rank < old_rank:
            stats["skipped_low_quality"] += 1
            stats["kept"] += 1
            continue
        by_key[k] = b
        stats["updated"] += 1
    out = sorted(by_key.values(), key=lambda x: (x["bin"], x.get("bank", "")))
    return out, stats


def build_report(
    mccs: list[dict[str, Any]],
    bins: list[dict[str, Any]],
    failed: list[str],
    mcc_stats: dict[str, int],
    bin_stats: dict[str, int],
    verified: str,
) -> dict[str, Any]:
    banks = sorted({b["bank"] for b in bins})
    brands: dict[str, int] = {}
    types: dict[str, int] = {}
    for b in bins:
        brands[b.get("cardBrand") or "Unknown"] = brands.get(b.get("cardBrand") or "Unknown", 0) + 1
        types[b.get("cardType") or "Unknown"] = types.get(b.get("cardType") or "Unknown", 0) + 1
    cb: dict[str, int] = {}
    for m in mccs:
        k = m.get("cashbackCategory") or "General"
        cb[k] = cb.get(k, 0) + 1
    return {
        "totalMcc": len(mccs),
        "totalBin": len(bins),
        "totalBanks": len(banks),
        "banks": banks,
        "binByBrand": brands,
        "binByType": types,
        "mccByCashback": dict(sorted(cb.items(), key=lambda x: -x[1])),
        "mccSource": MCC_SOURCE_LABEL,
        "binScope": "Vietnam only",
        "failedSources": failed,
        "mccDiff": mcc_stats,
        "binDiff": bin_stats,
        "coverageNotes": [
            "MCC list compiled from public greggles/mcc-codes.",
            "Vietnamese names curated for high-frequency retail/travel MCCs; others use English.",
            "Cashback categories are heuristic issuer practice, not network mandates.",
            "BIN list is curated Vietnam IIN/BIN from public Napas + community sources; not exhaustive.",
            'Never fabricate unknown BIN/level — display "Unknown".',
        ],
        "lastSync": verified,
    }


def write_db(payload: dict[str, Any], dry_run: bool) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if dry_run:
        print(f"[dry-run] would write {len(text)} bytes to {DATA_PATH} and {STATIC_PATH}")
        return
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATIC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(text, encoding="utf-8")
    STATIC_PATH.write_text(text, encoding="utf-8")
    print(f"Wrote {DATA_PATH.relative_to(ROOT)} and {STATIC_PATH.relative_to(ROOT)}")


def sync_mcc(existing: dict[str, Any] | None, verified: str, failed: list[str]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    try:
        raw = fetch_json(MCC_SOURCE_URL)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        failed.append(f"MCC fetch failed: {exc}")
        print(f"WARN: MCC fetch failed ({exc}); keeping existing MCC set", file=sys.stderr)
        return list((existing or {}).get("mccs") or []), {"added": 0, "updated": 0, "kept": 0, "skipped_low_quality": 0}

    incoming: list[dict[str, Any]] = []
    for row in raw:
        err = validate_mcc_row(row)
        if err:
            continue
        incoming.append(normalize_mcc(row, verified))
    return merge_mccs(incoming, (existing or {}).get("mccs"))


def sync_bin(existing: dict[str, Any] | None, verified: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    incoming = [normalize_bin(s, verified) for s in VN_BIN_SEED]
    return merge_bins(incoming, (existing or {}).get("bins"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync MCC + Vietnam BIN intelligence database")
    parser.add_argument("--mcc-only", action="store_true")
    parser.add_argument("--bin-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    verified = now_hcm()
    existing = load_existing()
    failed: list[str] = []

    if args.bin_only:
        mccs = list((existing or {}).get("mccs") or [])
        mcc_stats = {"added": 0, "updated": 0, "kept": 0, "skipped_low_quality": 0}
    else:
        mccs, mcc_stats = sync_mcc(existing, verified, failed)

    if args.mcc_only:
        bins = list((existing or {}).get("bins") or [])
        bin_stats = {"added": 0, "updated": 0, "kept": 0, "skipped_low_quality": 0}
    else:
        bins, bin_stats = sync_bin(existing, verified)

    if not mccs and not args.bin_only:
        print("ERROR: no MCC records after sync", file=sys.stderr)
        return 1

    report = build_report(mccs, bins, failed, mcc_stats, bin_stats, verified)
    payload = {
        "version": 1,
        "updatedAt": verified,
        "meta": report,
        "mccs": mccs,
        "bins": bins,
    }
    write_db(payload, dry_run=args.dry_run)
    print(
        f"MCC={report['totalMcc']} BIN={report['totalBin']} banks={report['totalBanks']} "
        f"mccDiff={mcc_stats} binDiff={bin_stats} failed={failed or 'none'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
