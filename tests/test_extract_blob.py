import re
from gcp_pricing.extract import find_blob, walk_blob


def _num(s):
    m = re.search(r"[\d,]+\.?\d*", s)
    return float(m.group().replace(",", "")) if m else None


def test_blob_found_and_regions(accel_html):
    data = find_blob(accel_html)
    assert data is not None
    regions, columns, records = walk_blob(data)
    codes = {r["code"] for r in regions}
    assert len(codes) >= 40                       # ~45 regions embedded
    assert "europe-west4" in codes                # Netherlands present
    assert all(r["name"].endswith(")") for r in regions)


def test_blob_known_machine_positive_prices(accel_html):
    _, _, records = walk_blob(find_blob(accel_html))
    hits = [r for r in records if r["item"] == "a3-megagpu-8g"
            and r["region_code"] == "us-central1" and r["unit"] == "hour"]
    assert len(hits) == 1                          # deduped to one widest row
    vals = [_num(v) for v in hits[0]["values"].values()]
    assert len(vals) >= 4 and all(v and v > 0 for v in vals)


def test_blob_dedupes_per_item_region_unit(accel_html):
    _, _, records = walk_blob(find_blob(accel_html))
    seen = [(r["item"], r["region_code"], r["unit"]) for r in records]
    assert len(seen) == len(set(seen))             # no duplicate (item, region, unit)
