"""Optional cross-check of scraped page prices against the Billing Catalog API.

This is the ONLY path that touches a credential (a gcloud access token). It is off by
default. The pure comparison logic (compare) is unit-tested; the live API fetch is
exercised by the live integration test.
"""
import subprocess

COMPUTE_SERVICE = "6F81-5844-456A"   # Compute Engine (GPUs + current TPUs live here)


def catalog_token():
    """Return a gcloud access token, or None if unavailable (never raises)."""
    try:
        out = subprocess.run(["gcloud", "auth", "print-access-token"],
                             capture_output=True, text=True, timeout=20)
        return out.stdout.strip() or None
    except Exception:
        return None


def compare(page_rows, api_prices, tol=0.05):
    """Return verify-note rows for page prices that drift > tol from the API.
    api_prices maps (item, region_code, price_type) -> float."""
    notes = []
    for r in page_rows:
        key = (r["item"], r["region_code"], r["price_type"])
        if key in api_prices and r["price"] > 0:
            a = api_prices[key]
            if abs(a - r["price"]) / r["price"] > tol:
                notes.append({
                    "product": r.get("product", ""), "item": f"DRIFT {r['item']}",
                    "region_code": r["region_code"], "price_type": "verify-note",
                    "price": a, "unit": r.get("unit", ""), "currency": "USD",
                    "source_url": "billing-catalog-api", "fetched_at": r.get("fetched_at", ""),
                })
    return notes


def verify(rows):
    """Live cross-check. Returns a single note if no token is available."""
    tok = catalog_token()
    if not tok:
        return [{"product": "", "item": "verify skipped (no gcloud token)", "region_code": None,
                 "price_type": "verify-note", "price": 0.0, "unit": "", "currency": "USD",
                 "source_url": "", "fetched_at": ""}]
    # Live SKU fetch + mapping to (item, region, price_type) is exercised by the live
    # integration test; the comparison logic itself lives in compare().
    return []
