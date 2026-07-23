from gcp_pricing.verify import compare


def test_compare_flags_large_drift():
    page = [{"item": "a3-megagpu-8g", "region_code": "us-central1",
             "price_type": "on-demand", "price": 90.0}]
    api = {("a3-megagpu-8g", "us-central1", "on-demand"): 45.0}   # 2x drift
    notes = compare(page, api)
    assert notes and notes[0]["price_type"] == "verify-note"
    assert "DRIFT" in notes[0]["item"]


def test_compare_silent_when_aligned():
    page = [{"item": "x", "region_code": "us-central1", "price_type": "on-demand", "price": 10.0}]
    api = {("x", "us-central1", "on-demand"): 10.02}              # within tolerance
    assert compare(page, api) == []
