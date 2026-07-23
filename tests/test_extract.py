from gcp_pricing.extract import extract


def _row_for(sheet, item, region_sub):
    for r in sheet["rows"]:
        if len(r) > 1 and r[1] == item and region_sub in (r[0] or ""):
            return r
    return None


def test_blob_sheet_headers_and_regions(accel_html):
    ex = extract(accel_html, "u")
    assert len(ex["sheets"]) == 1
    sh = ex["sheets"][0]
    assert sh["headers"][0] == "Region"
    assert "On-Demand (USD)" in sh["headers"]
    assert len({r[0] for r in sh["rows"]}) >= 40          # all-region


def test_blob_cells_align_to_headers_verbatim(accel_html):
    sh = extract(accel_html, "u")["sheets"][0]
    h = sh["headers"]
    oi = h.index("On-Demand (USD)")
    fi = h.index("DWS Flex-start price (USD)")
    # On-Demand present, passed through verbatim
    r = _row_for(sh, "a3-megagpu-8g", "us-central1")
    assert r and r[oi].startswith("$93.4")
    # H200 in europe-west4 has no On-Demand: the page shows "-", which must hold its column
    # slot so Flex is not shifted into the On-Demand position
    r = _row_for(sh, "a3-ultragpu-8g", "europe-west4")
    assert r and r[oi] == "-" and r[fi].startswith("$42.4")


def test_tpu_dumped_as_tables_with_current_gens(tpu_html):
    ex = extract(tpu_html, "u")
    text = " ".join(c for sh in ex["sheets"] for row in sh["rows"] for c in row)
    assert "Trillium" in text and "Ironwood" in text      # v6e + v7, absent from billing API


def test_storage_returns_tables(storage_html):
    ex = extract(storage_html, "u")
    assert ex["sheets"] and any(sh["rows"] for sh in ex["sheets"])
