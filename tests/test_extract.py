"""Regressions for the capture contract.

Every test here corresponds to something the previous selecting/parsing implementation
silently lost during a real cost analysis.
"""
import re

from gcp_pricing.extract import extract, page_text, table_sheets, find_blob, walk_blob


def test_captures_tables_with_no_dollar_sign(storage_html):
    """Minimum storage duration has no '$' anywhere. The old $-gate dropped it, along with
    free-tier limits and the operation-class definitions."""
    ex = extract(storage_html, "u")
    assert "30 days" in ex["text"] and "365 days" in ex["text"]
    assert "5 GB-months" in ex["text"]                      # free tier
    assert ex["coverage"]["tables"] > ex["coverage"]["tables_priced"]


def test_returns_every_table_not_just_priced_ones(storage_html):
    from bs4 import BeautifulSoup
    n_in_page = len(BeautifulSoup(storage_html, "lxml").find_all("table"))
    assert len(table_sheets(storage_html)) == n_in_page


def test_captures_prose_not_only_tables(storage_html):
    """Retrieval-fee and Autoclass terms live in paragraphs, not tables."""
    t = page_text(storage_html)
    assert "Retrieval" in t and "Autoclass" in t
    assert len(t) > 20000


def test_blob_rows_carry_region_and_cells(accel_html):
    rows = walk_blob(find_blob(accel_html))
    assert rows
    assert len({r for r, _ in rows}) >= 20
    assert all(cells for _r, cells in rows)


def test_accelerator_dash_placeholder_survives(accel_html):
    """H200 has no On-Demand in europe-west4; the page prints '-'. It must be captured
    verbatim, not dropped - dropping it is what once shifted Flex into the On-Demand slot."""
    ex = extract(accel_html, "u")
    hit = [r for r in ex["regions"]
           if "europe-west4" in r["region"] and "a3-ultragpu-8g" in r["cells"]]
    assert hit
    cells = hit[0]["cells"]
    assert "-" in cells and any("42.4" in c for c in cells)


def test_gpu_page_has_base_and_vws_models(gpus_html):
    """A region offering a single base GPU nests a level shallower; the old row-picker
    returned only the Virtual Workstation SKU for us-east4."""
    ex = extract(gpus_html, "u")
    east4 = [r["cells"] for r in ex["regions"] if "us-east4" in r["region"]]
    flat = " | ".join(c for cells in east4 for c in cells)
    assert "NVIDIA T4" in flat
    assert "$0.37" in flat and "$0.57" in flat        # base and vWS


def test_coverage_is_reported(storage_html):
    c = extract(storage_html, "u")["coverage"]
    assert c["tables"] > 0 and c["region_rows"] > 0 and c["text_chars"] > 0


def test_live_general_purpose_has_every_family(general_purpose_html):
    """The old block-picker returned n4d alone out of 14 families."""
    ex = extract(general_purpose_html, "u")
    shapes = {c for r in ex["regions"] for c in r["cells"]
              if re.fullmatch(r"[a-z]\d+[a-z]*-\w+-\d+\w*", c)}
    fams = {s.split("-")[0] for s in shapes}
    for f in ("c3", "c3d", "c4", "c4a", "c4d", "e2", "n1", "n2", "n2d", "n4", "n4a", "n4d",
              "t2a", "t2d"):
        assert f in fams, f"missing family {f}"


def test_cheapest_8vcpu_16gib_in_us_east4_is_n4a(general_purpose_html):
    """The query that was never run. n4a-highcpu-8 must beat c4a-highcpu-8."""
    ex = extract(general_purpose_html, "u")
    prices = {}
    for r in ex["regions"]:
        if "us-east4" not in r["region"]:
            continue
        cells = r["cells"]
        for i, c in enumerate(cells):
            if re.fullmatch(r"[a-z]\d+[a-z]*-\w+-8", c) and cells[i + 1:i + 3] == ["8", "16 GiB"]:
                m = re.match(r"\$([\d.]+) / 1 hour", cells[i + 3])
                if m:
                    prices.setdefault(c, float(m.group(1)))
    assert prices
    assert min(prices, key=prices.get) == "n4a-highcpu-8"
    assert prices["n4a-highcpu-8"] < prices["c4a-highcpu-8"]
