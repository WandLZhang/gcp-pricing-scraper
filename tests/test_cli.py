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


def test_json_sheets():
    code, out = _run(["file://" + FIX, "--json"])
    assert code == 0
    d = json.loads(out)
    assert d["sheets"] and d["sheets"][0]["headers"][0] == "Region"


def test_filter_is_and_over_row():
    code, out = _run(["file://" + FIX, "--filter", "h200", "--filter", "netherlands", "--json"])
    d = json.loads(out)
    rows = [r for sh in d["sheets"] for r in sh["rows"]]
    assert rows
    for r in rows:
        joined = " ".join(r).lower()
        assert "h200" in joined and "netherlands" in joined


def test_table_output_has_source_footer():
    code, out = _run(["file://" + FIX, "--filter", "a3-megagpu-8g"])
    assert code == 0
    assert "Source (open to verify)" in out and "a3-megagpu-8g" in out
