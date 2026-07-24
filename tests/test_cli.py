import contextlib
import io
import json
import os

import pytest

from gcp_pricing.cli import main

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "storage.html")
pytestmark = pytest.mark.skipif(not os.path.exists(FIX),
                                reason="fixture missing; run capture_fixtures.py")


def _run(args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(args)
    return code, out.getvalue()


def test_json_has_text_regions_and_coverage():
    code, out = _run(["file://" + FIX, "--json"])
    assert code == 0
    d = json.loads(out)
    assert d["text"] and "coverage" in d and "regions" in d


def test_writes_full_capture_file_holding_everything(tmp_path, monkeypatch):
    monkeypatch.setattr("gcp_pricing.cli.CAPTURE_DIR", str(tmp_path))
    code, out = _run(["file://" + FIX, "--filter", "nearline"])
    assert code == 0
    path = [l.split("FULL CAPTURE: ")[1] for l in out.splitlines()
            if l.startswith("FULL CAPTURE: ")][0]
    body = open(path, encoding="utf-8").read()
    # the file holds everything, not only what matched the filter
    assert "Nearline" in body and "Archive" in body and "30 days" in body


def test_no_match_still_captures_and_says_so(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("gcp_pricing.cli.CAPTURE_DIR", str(tmp_path))
    code, out = _run(["file://" + FIX, "--filter", "zzz-not-a-real-thing"])
    assert code == 0
    assert "FULL CAPTURE:" in out
    assert "grep the file" in capsys.readouterr().err


def test_coverage_footer_reports_unpriced_tables(tmp_path, monkeypatch):
    monkeypatch.setattr("gcp_pricing.cli.CAPTURE_DIR", str(tmp_path))
    code, out = _run(["file://" + FIX, "--filter", "nearline"])
    assert "tables (" in out and "priced)" in out and "region rows" in out
