from gcp_pricing.extract import extract_tables, extract


def test_tpu_tables_have_current_generations(tpu_html):
    columns, records = extract_tables(tpu_html)
    items = " ".join(r["item"] for r in records)
    assert "Trillium" in items          # v6e
    assert "Ironwood" in items          # v7 — absent from the Billing Catalog API
    vals = [v for r in records for v in r["values"].values() if v.strip().startswith("$")]
    assert vals


def test_extract_dispatches_blob_for_accel(accel_html):
    ex = extract(accel_html, "http://x/accelerator")
    assert ex["kind"] == "blob"
    assert len(ex["records"]) > 100


def test_extract_dispatches_tables_for_tpu(tpu_html):
    ex = extract(tpu_html, "http://x/tpu")
    assert ex["kind"] == "tables"
    assert ex["records"]


def test_extract_falls_back_to_tables_for_storage(storage_html):
    ex = extract(storage_html, "http://x/storage")
    assert ex["kind"] == "tables"       # blob present but no block structure -> tables
