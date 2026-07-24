"""Curated product -> canonical page URL(s). Anything not here still works via a raw URL
or the resolver's pattern probe."""
BASE = "https://cloud.google.com"
DOCS = "https://docs.cloud.google.com"

PRODUCTS = {
    "vms": [f"{BASE}/products/compute/pricing/general-purpose?hl=en",
            f"{BASE}/products/compute/pricing/compute-optimized?hl=en",
            f"{BASE}/products/compute/pricing/memory-optimized?hl=en",
            f"{BASE}/products/compute/pricing/storage-optimized?hl=en",
            f"{BASE}/products/compute/pricing/accelerator-optimized?hl=en"],
    "general-purpose": [f"{BASE}/products/compute/pricing/general-purpose?hl=en"],
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
    "generative-ai": [f"{BASE}/vertex-ai/generative-ai/pricing?hl=en"],
    "managed-spark": [f"{BASE}/products/managed-service-for-apache-spark/pricing?hl=en"],
    "dataflow": [f"{BASE}/dataflow/pricing?hl=en"],
    "support": [f"{BASE}/support"],
    "sud": [f"{DOCS}/compute/docs/sustained-use-discounts"],
}

ALIASES = {
    "vm": "vms", "gpus": "gpu", "accelerators": "accelerator", "accel": "accelerator",
    "gcs": "storage", "cloud-storage": "storage", "rapid": "storage",
    "bq": "bigquery", "run": "cloud-run", "cloudrun": "cloud-run",
    "kubernetes": "gke", "sql": "cloud-sql", "cloudsql": "cloud-sql",
    "vertex": "vertex-ai", "agent-platform": "vertex-ai", "workbench": "vertex-ai",
    "managed-lustre": "lustre",
    "genai": "generative-ai", "gemini": "generative-ai", "claude": "generative-ai",
    "dataproc": "managed-spark", "spark": "managed-spark",
    "dataproc-serverless": "managed-spark", "apache-spark": "managed-spark",
    "customer-care": "support", "enhanced-support": "support",
    "sustained-use": "sud", "suds": "sud",
    "gp": "general-purpose",
}

# Billing Catalog API service IDs. Pages and the catalog each omit things the other has,
# so both are first-class sources.
CATALOG_SERVICES = {
    "notebooks": "D73B-5EEA-8215",      # Workbench / Managed Notebooks GPU SKUs
    "vertex-ai": "D73B-5EEA-8215",
    "workbench": "D73B-5EEA-8215",
    "compute": "6F81-5844-456A",        # Compute Engine: GPUs + current TPUs
    "vms": "6F81-5844-456A",
    "gpu": "6F81-5844-456A",
    "tpu": "6F81-5844-456A",
}
