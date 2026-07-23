import pytest
from gcp_pricing.fetch import fetch
from gcp_pricing.extract import extract

pytestmark = pytest.mark.live


def test_live_accelerator_all_regions():
    ex = extract(fetch("https://cloud.google.com/products/compute/pricing/accelerator-optimized?hl=en"), "u")
    sh = ex["sheets"][0]
    assert "On-Demand (USD)" in sh["headers"]
    assert len({r[0] for r in sh["rows"]}) >= 40


def test_live_tpu_has_ironwood_and_trillium():
    ex = extract(fetch("https://cloud.google.com/tpu/pricing?hl=en"), "u")
    text = " ".join(c for sh in ex["sheets"] for row in sh["rows"] for c in row)
    assert "Trillium" in text and "Ironwood" in text
