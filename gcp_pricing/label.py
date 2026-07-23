"""Turn an Extraction into typed PriceRows.

Price-type labeling uses a frozen name_map (schema.json) authored by inspecting real
pages — the "let an LLM read the labels, don't regex them" rule, cached to disk. Column
names come from the page itself (visible table headers), so the map is small and robust.
"""
import json
import os
import re
from datetime import datetime, timezone

_SCHEMA = os.path.join(os.path.dirname(__file__), "schema.json")


def load_schema():
    with open(_SCHEMA) as f:
        return json.load(f)


def _to_float(s):
    m = re.search(r"[\d,]+\.?\d*", s)          # numeric token extraction, not prose parsing
    return float(m.group().replace(",", "")) if m else None


def _unit_from(s, default="hour"):
    low = s.lower()
    if "month" in low:
        return "month"
    if "hour" in low:
        return "hour"
    return default


def _now():
    return datetime.now(timezone.utc).isoformat()


def _canon(colname, name_map):
    low = colname.lower()
    for substr, canon in name_map:
        if substr.lower() in low:
            return canon, False
    cleaned = colname.split(" (USD)")[0].strip() or colname
    return (cleaned or "unknown"), True


def label(ex, product, schema):
    """Return list[PriceRow]. Only $-valued cells become rows; region/spec cells are skipped."""
    name_map = schema["name_map"]
    cols = ex.get("columns", [])
    kind = ex.get("kind")
    now = _now()
    rows = []
    for rec in ex["records"]:
        for key, raw in rec["values"].items():
            if not raw.strip().startswith("$"):
                continue
            price = _to_float(raw)
            if price is None:
                continue
            if kind == "blob" and str(key).isdigit() and int(key) < len(cols):
                colname = cols[int(key)]
            else:
                colname = str(key)
            price_type, is_raw = _canon(colname, name_map)
            unit = _unit_from(raw, default=(rec.get("unit") or "hour"))   # per-cell, not per-row
            rows.append({
                "product": product, "item": rec.get("item", ""),
                "attrs": {"desc": rec.get("desc", [])},
                "region_code": rec.get("region_code"), "region_name": rec.get("region_name"),
                "price_type": price_type, "unit": unit, "price": price, "currency": "USD",
                "source_url": ex.get("source_url", ""), "fetched_at": now, "raw": is_raw,
            })
    # dedupe: the page splits one region across blocks, so a rate can appear twice
    out, seen = [], set()
    for row in rows:
        k = (row["item"], row["region_code"], row["price_type"], row["unit"])
        if k in seen:
            continue
        seen.add(k)
        out.append(row)
    return out
