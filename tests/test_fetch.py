import pytest
from gcp_pricing.fetch import fetch, FetchError


def test_fetch_reads_local_file(tmp_path):
    p = tmp_path / "x.html"
    p.write_text("<html>hi</html>")
    assert "hi" in fetch(p.as_uri())


def test_fetch_raises_clear_error_on_bad_host():
    with pytest.raises(FetchError):
        fetch("https://cloud.google.invalid/nope")
