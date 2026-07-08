#!/usr/bin/env python3
"""Download and process 13 unique images for Thailand rainy season series."""

import os
import json
import hashlib
from PIL import Image
import requests

POSTS_DIR = "static/images/posts"
os.makedirs(POSTS_DIR, exist_ok=True)

# 13 unique images from Pexels (all Pexels License, free commercial use)
IMAGES = [
    {
        "slug": "du-lich-thai-lan-mua-mua-co-nen-di-khong",
        "url": "https://images.pexels.com/photos/10119144/pexels-photo-10119144.jpeg",
        "credit": "Photo by Varvara Grabina",
        "source_url": "https://www.pexels.com/photo/wat-phra-singh-in-chiang-rai-thailand-10119144/",
    },
    {
        "slug": "di-thai-lan-thang-7-co-nen-khong",
        "url": "https://images.pexels.com/photos/31026228/pexels-photo-31026228.jpeg",
        "credit": "Photo by Teera Noisakran",
        "source_url": "https://www.pexels.com/photo/scenic-riverside-in-bangkok-with-thai-architecture-31026228/",
    },
    {
        "slug": "bangkok-ngay-mua-nen-di-dau",
        "url": "https://images.pexels.com/photos/27662996/pexels-photo-27662996.jpeg",
        "credit": "Photo by Benjamín B.",
        "source_url": "https://www.pexels.com/photo/siam-paragon-shopping-mall-in-bangkok-27662996/",
    },
    {
        "slug": "bangkok-3-ngay-3-dem-mua-mua",
        "url": "https://images.pexels.com/photos/37835945/pexels-photo-37835945.jpeg",
        "credit": "Photo by Steffen B.",
        "source_url": "https://www.pexels.com/photo/bangkok-cityscape-at-sunset-with-traffic-37835945/",
    },
    {
        "slug": "phuket-mua-mua-co-nen-di-khong",
        "url": "https://images.pexels.com/photos/36687407/pexels-photo-36687407.jpeg",
        "credit": "Photo by Damir Babacic",
        "source_url": "https://www.pexels.com/photo/tropical-beach-in-phuket-thailand-with-scenic-views-36687407/",
    },
    {
        "slug": "krabi-mua-mua-ao-nang-railay-tour-dao",
        "url": "https://images.pexels.com/photos/27104227/pexels-photo-27104227.jpeg",
        "credit": "Photo by Andre Furtado",
        "source_url": "https://www.pexels.com/photo/railay-beach-in-krabi-thailand-27104227/",
    },
    {
        "slug": "koh-samui-mua-he-so-voi-phuket",
        "url": "https://images.pexels.com/photos/9103211/pexels-photo-9103211.jpeg",
        "credit": "Photo by SevenStorm JUHASZIMRUS",
        "source_url": "https://www.pexels.com/photo/aerial-view-of-koh-samui-beach-9103211/",
    },
    {
        "slug": "chiang-mai-mua-mua-co-gi-dep",
        "url": "https://images.pexels.com/photos/14211124/pexels-photo-14211124.jpeg",
        "credit": "Photo by Sittichai J.",
        "source_url": "https://www.pexels.com/photo/golden-buddha-statue-at-doi-suthep-chiang-mai-14211124/",
    },
    {
        "slug": "doi-baht-o-viet-nam-hay-thai-lan",
        "url": "https://images.pexels.com/photos/730564/pexels-photo-730564.jpeg",
        "credit": "Photo by Quang Nguyen Vinh",
        "source_url": "https://www.pexels.com/photo/thai-baht-banknotes-and-coins-730564/",
    },
    {
        "slug": "suvarnabhumi-ve-trung-tam-bangkok-arl-bts-taxi-grab",
        "url": "https://images.pexels.com/photos/27941933/pexels-photo-27941933.jpeg",
        "credit": "Photo by Apichart Srisung",
        "source_url": "https://www.pexels.com/photo/ancient-city-bangkok-27941933/",
    },
    {
        "slug": "o-khu-nao-bangkok-mua-mua",
        "url": "https://images.pexels.com/photos/28503555/pexels-photo-28503555.jpeg",
        "credit": "Photo by Teera Noisakran",
        "source_url": "https://www.pexels.com/photo/bangkok-skytrain-bts-at-siam-station-28503555/",
    },
    {
        "slug": "checklist-vali-di-thai-mua-mua",
        "url": "https://images.pexels.com/photos/4245895/pexels-photo-4245895.jpeg",
        "credit": "Photo by Karolina Grabowska",
        "source_url": "https://www.pexels.com/photo/couple-packing-clothes-and-belongings-in-suitcase-4245895/",
    },
    {
        "slug": "ubon-ratchathani-candle-festival-thai-lan-thang-7",
        "url": "https://images.pexels.com/photos/5712567/pexels-photo-5712567.jpeg",
        "credit": "Photo by Thongchai S.",
        "source_url": "https://www.pexels.com/photo/thai-candle-festival-sculpture-5712567/",
    },
]

def download_and_process(item):
    slug = item["slug"]
    output_path = os.path.join(POSTS_DIR, f"{slug}.webp")

    if os.path.exists(output_path):
        print(f"  Already exists: {slug}.webp")
        return True

    print(f"  Downloading: {slug}...")
    try:
        resp = requests.get(item["url"], timeout=30, stream=True)
        if resp.status_code != 200:
            print(f"    Failed: HTTP {resp.status_code}")
            return False

        # Save temp
        tmp_path = f"/tmp/{slug}.jpg"
        with open(tmp_path, "wb") as f:
            f.write(resp.content)

        # Process to WebP
        img = Image.open(tmp_path).convert("RGB")
        target_w, target_h = 800, 450
        img_w, img_h = img.size
        target_ratio = target_w / target_h
        img_ratio = img_w / img_h

        if img_ratio > target_ratio:
            new_w = int(img_h * target_ratio)
            offset = (img_w - new_w) // 2
            img = img.crop((offset, 0, offset + new_w, img_h))
        elif img_ratio < target_ratio:
            new_h = int(img_w / target_ratio)
            offset = (img_h - new_h) // 2
            img = img.crop((0, offset, img_w, offset + new_h))

        img = img.resize((target_w, target_h), Image.LANCZOS)
        img.save(output_path, "WebP", quality=85)
        os.remove(tmp_path)
        print(f"    Saved: {slug}.webp")
        return True
    except Exception as e:
        print(f"    Error: {e}")
        return False

def main():
    print("=== Downloading and processing images ===\n")
    success = 0
    failed = 0
    for item in IMAGES:
        ok = download_and_process(item)
        if ok:
            success += 1
        else:
            failed += 1
    print(f"\nDone: {success} success, {failed} failed")

if __name__ == "__main__":
    main()
