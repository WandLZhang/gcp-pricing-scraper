"""Cloud Billing Catalog API lookup.

Pricing pages omit SKUs. The Vertex/Agent Platform page's us-east4 Workbench-Instances
accelerator table lists only A100 variants, which reads as "T4 not offered"; the catalog
carries `Workbench Instances GPU for GCE usage - T4 in us-east4` at $0.444/hr. So the gap
runs both ways, and an absent row on a page is never proof of absence.

Auth is whatever `gcloud auth print-access-token` yields - no API key, no new credential.
"""
import json
import subprocess
import urllib.error
import urllib.request

from .registry import CATALOG_SERVICES

API = "https://cloudbilling.googleapis.com/v1"


class CatalogError(Exception):
    pass


def _token():
    try:
        out = subprocess.run(["gcloud", "auth", "print-access-token"],
                             capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise CatalogError(f"could not run gcloud: {e}")
    if out.returncode != 0:
        raise CatalogError(f"gcloud auth failed: {out.stderr.strip()}")
    return out.stdout.strip()


def _get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=90))
    except urllib.error.HTTPError as e:
        raise CatalogError(f"catalog API {e.code}: {e.reason}")


def find_service(name, token):
    """Service ID for a product name. Known ones are cached; otherwise scan displayNames."""
    key = name.lower()
    if key in CATALOG_SERVICES:
        return CATALOG_SERVICES[key]
    page, want = "", key.replace("-", " ")
    while True:
        d = _get(f"{API}/services?pageSize=500" + (f"&pageToken={page}" if page else ""), token)
        for s in d.get("services", []):
            if want in s["displayName"].lower():
                return s["serviceId"]
        page = d.get("nextPageToken", "")
        if not page:
            raise CatalogError(
                f"no Billing Catalog service matches '{name}'. Known: "
                + ", ".join(sorted(CATALOG_SERVICES)))


def catalog_skus(target, terms):
    """SKUs for a product, filtered by substring AND over description + regions."""
    token = _token()
    sid = target if target.count("-") == 2 and target.isupper() else find_service(target, token)
    out, page = [], ""
    while True:
        d = _get(f"{API}/services/{sid}/skus?pageSize=5000" + (f"&pageToken={page}" if page else ""),
                 token)
        for s in d.get("skus", []):
            hay = (s["description"] + " " + " ".join(s.get("serviceRegions") or [])).lower()
            if terms and not all(t in hay for t in terms):
                continue
            pi = s["pricingInfo"][0]["pricingExpression"]
            tier = pi["tieredRates"][-1]["unitPrice"]
            out.append({
                "description": s["description"],
                "regions": s.get("serviceRegions") or [],
                "unit": pi.get("usageUnitDescription", ""),
                "price": int(tier.get("units", 0)) + tier.get("nanos", 0) / 1e9,
                "resource_group": s["category"].get("resourceGroup"),
            })
        page = d.get("nextPageToken", "")
        if not page:
            break
    out.sort(key=lambda s: s["description"])
    return out
