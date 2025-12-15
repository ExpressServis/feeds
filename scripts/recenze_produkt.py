import json
import time
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
import os
import hashlib
from collections import defaultdict

KEY = os.environ["HEUREKA_KEY"]
FEED_URL = f"https://www.heureka.cz/direct/dotaznik/export-product-review.php?key={KEY}"

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

def norm(s: str) -> str:
    return " ".join((s or "").strip().split())

def fingerprint(item: dict) -> str:
    # schválně nepoužíváme rating_id (může se měnit)
    base = "|".join([
        str(item.get("unix_timestamp", 0) or 0),
        str(item.get("rating", "")),
        norm(item.get("pros", "")),
        norm(item.get("cons", "")),
        norm(item.get("summary", "")),
        str(item.get("recommends", "")),
    ])
    return hashlib.sha1(base.encode("utf-8")).hexdigest()

r = requests.get(FEED_URL, timeout=25)
r.raise_for_status()

root = ET.fromstring(r.text)

products = []
raw_reviews_total = 0
saved_reviews_total = 0
dupes_within_product = 0

# pro přehled: stejná recenze napříč produkty (typicky offer->product párování)
fp_to_products = defaultdict(list)

for p in root.findall("product"):
    product_name = txt(p, "product_name")
    url = txt(p, "url")
    price = fnum(txt(p, "price"))
    ean = txt(p, "ean")

    reviews_node = p.find("reviews")
    product_reviews = []
    seen_in_product = set()

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

            raw_reviews_total += 1

            fp = fingerprint(item)
            item["fingerprint"] = fp

            # deduplikace jen UVNITŘ produktu (když export někdy zopakuje stejnou recenzi)
            if fp in seen_in_product:
                dupes_within_product += 1
                continue

            seen_in_product.add(fp)
            product_reviews.append(item)

            fp_to_products[fp].append({
                "ean": ean,
                "url": url,
                "product_name": product_name,
            })

    # seřadit recenze u produktu od nejnovějších
    product_reviews.sort(key=lambda x: x.get("unix_timestamp", 0), reverse=True)

    saved_reviews_total += len(product_reviews)

    products.append({
        "product_name": product_name,
        "url": url,
        "price": price,
        "ean": ean,
        "reviews_count": len(product_reviews),
        "reviews": product_reviews
    })

def newest_ts(prod):
    rv = prod.get("reviews") or []
    return rv[0].get("unix_timestamp", 0) if rv else 0

products.sort(key=newest_ts, reverse=True)

# kolik fingerprintů se objevilo u více produktů
cross_product_dupes = {fp: lst for fp, lst in fp_to_products.items() if len(lst) > 1}

payload = {
    "generated_at": int(time.time()),
    "stats": {
        "products_count": len(products),
        "raw_reviews_in_feed": raw_reviews_total,
        "saved_reviews": saved_reviews_total,
        "duplicates_within_product_skipped": dupes_within_product,
        "cross_product_duplicates_count": len(cross_product_dupes),
    },
    # pro audit – můžeš kdykoli vypnout, pokud je to moc velké
    "cross_product_duplicates": cross_product_dupes,
    "products": products
}

OUT.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(
    "OK:",
    f"products={len(products)}",
    f"raw_reviews={raw_reviews_total}",
    f"saved_reviews={saved_reviews_total}",
    f"dupes_within_product_skipped={dupes_within_product}",
    f"cross_product_duplicates={len(cross_product_dupes)}",
    "->", OUT
)
