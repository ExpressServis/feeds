import json
import time
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

FEED_URL = "https://www.heureka.cz/direct/dotaznik/export-product-review.php?key=4e374a9eda4003d683ecb1fea6cf1d80"
# volitelně: omez od data (viz tip v zadání)
# FEED_URL += "&from=2025-10-01 00:00:00"

OUT = Path("data/heureka_product_reviews.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

def txt(node, tag):
    el = node.find(tag)
    return (el.text or "").strip() if el is not None else ""

def fnum(s):
    s = (s or "").replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return None

def inum(s, default=0):
    try:
        return int((s or "").strip() or default)
    except ValueError:
        return default

r = requests.get(FEED_URL, timeout=25)
r.raise_for_status()

root = ET.fromstring(r.text)

products = []
total_reviews = 0

# Kořen: <products>
for p in root.findall("product"):
    product_name = txt(p, "product_name")
    url = txt(p, "url")
    price = fnum(txt(p, "price"))
    ean = txt(p, "ean")

    reviews_node = p.find("reviews")
    product_reviews = []

    if reviews_node is not None:
        for rv in reviews_node.findall("review"):
            item = {
                "rating_id": txt(rv, "rating_id"),
                "rating_id_type": txt(rv, "rating_id_type"),  # offer|product
                "unix_timestamp": inum(txt(rv, "unix_timestamp")),
                "rating": fnum(txt(rv, "rating")),
                "pros": txt(rv, "pros"),
                "cons": txt(rv, "cons"),
                "summary": txt(rv, "summary"),
                "recommends": txt(rv, "recommends"),
            }
            product_reviews.append(item)

    # seřadit recenze u produktu od nejnovějších
    product_reviews.sort(key=lambda x: x.get("unix_timestamp", 0), reverse=True)

    total_reviews += len(product_reviews)

    products.append({
        "product_name": product_name,
        "url": url,
        "price": price,  # bez DPH dle specifikace
        "ean": ean,
        "reviews_count": len(product_reviews),
        "reviews": product_reviews
    })

# volitelně: seřadit produkty podle nejnovější recenze (kdo má nejnovější, jde nahoru)
def newest_ts(prod):
    rv = prod.get("reviews") or []
    return rv[0].get("unix_timestamp", 0) if rv else 0

products.sort(key=newest_ts, reverse=True)

payload = {
    "generated_at": int(time.time()),
    "products_count": len(products),
    "reviews_count": total_reviews,
    "products": products
}

OUT.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(f"OK: saved {len(products)} products / {total_reviews} reviews -> {OUT}")
