from gcp_pricing.resolver import resolve


def test_known_product_maps_to_urls():
    r = resolve("tpu")
    assert r["resolved_by"] == "registry"
    assert any("tpu/pricing" in u for u in r["urls"])


def test_alias_maps():
    assert resolve("gcs")["urls"] == resolve("storage")["urls"]


def test_hub_product_expands_to_subpages():
    r = resolve("vms")
    assert len(r["urls"]) >= 4


def test_raw_url_passthrough():
    r = resolve("https://cloud.google.com/spanner/pricing")
    assert r["resolved_by"] == "passthrough"
    assert r["urls"] == ["https://cloud.google.com/spanner/pricing"]


def test_unknown_word_returns_pattern_candidates():
    r = resolve("totally-made-up-xyz")
    assert r["resolved_by"] == "pattern"
    assert all("pricing" in u for u in r["urls"])
