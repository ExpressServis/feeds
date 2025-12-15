import json
import time
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

FEED_URL = "https://www.heureka.cz/direct/dotaznik/export-review.php?key=4e374a9eda4003d683ecb1fea6cf1d80"
OUT = Path("data/heureka_reviews.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

def txt(node, tag):
    el = node.find(tag)
    return (el.text or "").strip() if el is not None else ""

def fnum(s):
    s = (s or "").replace(",", ".").strip()
    try:
        return float(s)
    except:
        return None

r = requests.get(FEED_URL, timeout=20)
r.raise_for_status()

root = ET.fromstring(r.text)
reviews = []

for rv in root.findall("review"):
    item = {
        "rating_id": txt(rv, "rating_id"),
        "ordered": int(txt(rv, "ordered") or 0),
        "unix_timestamp": int(txt(rv, "unix_timestamp") or 0),
        "total_rating": fnum(txt(rv, "total_rating")),
        "delivery_time": fnum(txt(rv,_
