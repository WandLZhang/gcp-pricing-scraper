"""Download real GCP pricing pages into tests/fixtures/. Run once before tests:
   python tests/capture_fixtures.py
Fixtures are gitignored (large) and are real page captures, not mock data."""
import os
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
PAGES = {
    "accelerator.html": "https://cloud.google.com/products/compute/pricing/accelerator-optimized?hl=en",
    "tpu.html": "https://cloud.google.com/tpu/pricing?hl=en",
    "bigquery.html": "https://cloud.google.com/bigquery/pricing?hl=en",
    "storage.html": "https://cloud.google.com/storage/pricing?hl=en",
}


def main():
    here = os.path.join(os.path.dirname(__file__), "fixtures")
    os.makedirs(here, exist_ok=True)
    for name, url in PAGES.items():
        req = urllib.request.Request(url, headers=UA)
        html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        with open(os.path.join(here, name), "w", encoding="utf-8") as f:
            f.write(html)
        print(f"captured {name}: {len(html)} bytes")


if __name__ == "__main__":
    main()
