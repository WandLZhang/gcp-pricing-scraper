from gcp_pricing.extract import extract
from gcp_pricing.label import load_schema, label


def test_accel_rows_are_typed(accel_html):
    rows = label(extract(accel_html, "http://x/accelerator"), "accelerator", load_schema())
    types = {r["price_type"] for r in rows}
    assert {"on-demand", "spot", "flex", "calendar", "cud-1y", "cud-3y"} <= types
    assert all(isinstance(r["price"], float) and r["price"] > 0 for r in rows)
    r0 = rows[0]
    assert r0["source_url"] and r0["fetched_at"] and r0["currency"] == "USD"


def test_ondemand_ge_cud3y_same_item_region(accel_html):
    rows = label(extract(accel_html, "u"), "accelerator", load_schema())
    by = {}
    for r in rows:
        if r["unit"] != "hour":
            continue
        by.setdefault((r["item"], r["region_code"]), {})[r["price_type"]] = r["price"]
    checked = 0
    for m in by.values():
        if m.get("on-demand") and m.get("cud-3y"):
            assert m["on-demand"] >= m["cud-3y"]     # economic invariant: commit <= on-demand
            checked += 1
    assert checked > 0


def test_tpu_on_demand_labeled(tpu_html):
    rows = label(extract(tpu_html, "http://x/tpu"), "tpu", load_schema())
    tri = [r for r in rows if r["item"] == "Trillium" and r["price_type"] == "on-demand"]
    assert tri and all(r["price"] > 0 for r in tri)


def test_rows_carry_raw_value_and_column(accel_html):
    rows = label(extract(accel_html, "u"), "accelerator", load_schema())
    r = next(r for r in rows if r["item"] == "a3-megagpu-8g" and r["price_type"] == "on-demand")
    assert r["value"].startswith("$") and "/" in r["value"]   # raw page string, intact
    assert "USD" in r["column"]                                # page's own column label


def test_unknown_column_kept_verbatim():
    ex = {"kind": "blob", "columns": ["Weird Metric"], "source_url": "u",
          "records": [{"item": "x", "region_code": "us-central1", "region_name": None,
                       "unit": "hour", "desc": ["x"], "values": {"0": "$1.00 / 1 hour"}}]}
    rows = label(ex, "accelerator", load_schema())
    assert rows
    r = rows[0]
    assert r["column"] == "Weird Metric"      # page's own label preserved verbatim
    assert r["value"] == "$1.00 / 1 hour"     # raw string preserved
    assert r["price_type"] == "Weird Metric"  # convenience label falls back to the raw column
