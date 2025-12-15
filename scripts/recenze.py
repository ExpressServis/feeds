import json
import time
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
import os

KEY = os.environ["HEUREKA_KEY"]
FEED_URL = f"https://www.heureka.cz/direct/dotaznik/export-review.php?key={KEY}"
OUT = Path("data/heureka_reviews.json")
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

r = requests.get(FEED_URL, timeout=25)
r.raise_for_status()

root = ET.fromstring(r.text)
reviews = []

for rv in root.findall("review"):
    reviews.append({
        "rating_id": txt(rv, "rating_id"),
        "ordered": int(txt(rv, "ordered") or 0),
        "unix_timestamp": int(txt(rv, "unix_timestamp") or 0),
        "total_rating": fnum(txt(rv, "total_rating")),
        "delivery_time": fnum(txt(rv, "delivery_time")),
        "transport_quality": fnum(txt(rv, "transport_quality")),
        "web_usability": fnum(txt(rv, "web_usability")),
        "communication": fnum(txt(rv, "communication")),
        "pros": txt(rv, "pros"),
        "cons": txt(rv, "cons"),
        "summary": txt(rv, "summary"),
        "reaction": txt(rv, "reaction"),
        "recommends": txt(rv, "recommends"),
    })

# seřadit od nejnovějších
reviews.sort(key=lambda x: x.get("unix_timestamp", 0), reverse=True)

payload = {
    "generated_at": int(time.time()),
    "count": len(reviews),
    "reviews": reviews
}

OUT.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(f"OK: saved {len(reviews)} reviews -> {OUT}")
