import pytest
from gcp_pricing.fetch import fetch
from gcp_pricing.extract import extract
from gcp_pricing.label import load_schema, label

pytestmark = pytest.mark.live


def test_live_tpu_has_ironwood_and_trillium():
    ex = extract(fetch("https://cloud.google.com/tpu/pricing?hl=en"), "tpu")
    items = " ".join(r["item"] for r in ex["records"])
    assert "Trillium" in items and "Ironwood" in items


def test_live_accelerator_all_regions_typed():
    ex = extract(fetch("https://cloud.google.com/products/compute/pricing/accelerator-optimized?hl=en"),
                 "accelerator")
    rows = label(ex, "accelerator", load_schema())
    regions = {r["region_code"] for r in rows}
    types = {r["price_type"] for r in rows}
    assert len(regions) >= 40
    assert {"on-demand", "spot", "cud-3y"} <= types
    assert all(r["price"] > 0 for r in rows)
