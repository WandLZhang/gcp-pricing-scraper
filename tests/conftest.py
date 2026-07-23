import os
import pytest

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _load(name):
    path = os.path.join(FIX, name)
    if not os.path.exists(path):
        pytest.skip(f"fixture {name} missing; run: python tests/capture_fixtures.py")
    return open(path, encoding="utf-8").read()


@pytest.fixture
def accel_html():
    return _load("accelerator.html")


@pytest.fixture
def tpu_html():
    return _load("tpu.html")


@pytest.fixture
def bigquery_html():
    return _load("bigquery.html")


@pytest.fixture
def storage_html():
    return _load("storage.html")
