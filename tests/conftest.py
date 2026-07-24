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


@pytest.fixture
def gpus_html():
    return _load("gpus.html")


@pytest.fixture
def managed_spark_html():
    return _load("managed-spark.html")


@pytest.fixture(scope="session")
def general_purpose_html():
    """32 MB; session-scoped so the whole suite pays the read once."""
    return _load("general-purpose.html")
