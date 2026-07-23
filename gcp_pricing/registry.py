"""Curated product -> canonical pricing URL(s). Anything not here still works via a raw
URL or the resolver's pattern probe."""
BASE = "https://cloud.google.com"

PRODUCTS = {
    "vms": [f"{BASE}/products/compute/pricing/general-purpose?hl=en",
            f"{BASE}/products/compute/pricing/compute-optimized?hl=en",
            f"{BASE}/products/compute/pricing/memory-optimized?hl=en",
            f"{BASE}/products/compute/pricing/storage-optimized?hl=en",
            f"{BASE}/products/compute/pricing/accelerator-optimized?hl=en"],
    "accelerator": [f"{BASE}/products/compute/pricing/accelerator-optimized?hl=en"],
    "gpu": [f"{BASE}/products/compute/pricing/accelerator-optimized?hl=en",
            f"{BASE}/products/compute/gpus-pricing?hl=en"],
    "tpu": [f"{BASE}/tpu/pricing?hl=en"],
    "storage": [f"{BASE}/storage/pricing?hl=en"],
    "lustre": [f"{BASE}/products/managed-lustre/pricing?hl=en"],
    "parallelstore": [f"{BASE}/parallelstore/pricing?hl=en"],
    "bigquery": [f"{BASE}/bigquery/pricing?hl=en"],
    "cloud-run": [f"{BASE}/run/pricing?hl=en"],
    "gke": [f"{BASE}/kubernetes-engine/pricing?hl=en"],
    "spanner": [f"{BASE}/spanner/pricing?hl=en"],
    "cloud-sql": [f"{BASE}/sql/pricing?hl=en"],
    "vertex-ai": [f"{BASE}/vertex-ai/pricing?hl=en"],
}

ALIASES = {
    "vm": "vms", "gpus": "gpu", "accelerators": "accelerator", "accel": "accelerator",
    "gcs": "storage", "cloud-storage": "storage", "rapid": "storage",
    "bq": "bigquery", "run": "cloud-run", "cloudrun": "cloud-run",
    "kubernetes": "gke", "sql": "cloud-sql", "cloudsql": "cloud-sql",
    "vertex": "vertex-ai", "managed-lustre": "lustre",
}
