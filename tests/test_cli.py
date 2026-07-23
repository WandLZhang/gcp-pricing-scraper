import json
import os
import io
import contextlib
import pytest
from gcp_pricing.cli import main

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "accelerator.html")
pytestmark = pytest.mark.skipif(not os.path.exists(FIX), reason="fixture missing; run capture_fixtures.py")


def _run(args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(args)
    return code, out.getvalue()


def test_json_output_all_regions():
    code, out = _run(["file://" + FIX, "--product", "accelerator", "--all-regions", "--json"])
    assert code == 0
    rows = json.loads(out)
    assert rows and {"price", "price_type", "region_code", "source_url", "item"} <= set(rows[0])


def test_region_filter():
    code, out = _run(["file://" + FIX, "--product", "accelerator", "--region", "europe-west4", "--json"])
    rows = json.loads(out)
    assert rows and all(r["region_code"] == "europe-west4" for r in rows)


def test_table_output_has_source_footer():
    code, out = _run(["file://" + FIX, "--product", "accelerator", "--filter", "a3-megagpu-8g"])
    assert code == 0
    assert "Source (open to verify)" in out and "a3-megagpu-8g" in out
