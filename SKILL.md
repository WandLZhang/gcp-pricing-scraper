---
name: gcp-pricing
description: Get live Google Cloud pricing for ANY product (VMs, GPUs, TPUs, BigQuery, storage, Lustre, Spanner, ...). Use whenever asked for a GCP price, cost, rate, or $/hr — the official pricing pages are JS-rendered so WebFetch fails; this scrapes their embedded data instead.
---

# gcp-pricing

A zero-auth CLI that returns current Google Cloud pricing by scraping the official
`cloud.google.com/**/pricing` pages (their numbers are embedded in the page; WebFetch
only sees the empty shell). All regions, all price types.

## Use it

Run the CLI with your Bash tool and read stdout:

```
gcp-pricing <product|url> [--region CODE ... | --all-regions] [--json] [--filter TEXT] [--verify]
```

Examples:
- `gcp-pricing accelerator --region us-central1` — GPU VM node pricing (per-VM TCO)
- `gcp-pricing gpu --all-regions --json` — per-chip GPU pricing, every region
- `gcp-pricing tpu --filter Trillium` — TPU incl. Ironwood/v7 and Trillium (not in the billing API)
- `gcp-pricing bigquery --filter slots`
- `gcp-pricing storage --filter rapid`
- `gcp-pricing https://cloud.google.com/spanner/pricing` — any page by URL

Known product names: `vms, accelerator, gpu, tpu, storage, lustre, parallelstore,
bigquery, cloud-run, gke, spanner, cloud-sql, vertex-ai` (plus aliases). Anything else:
pass the pricing URL directly, or the tool will pattern-guess it.

## Notes for the agent

- Default output is a table; add `--json` for structured rows.
- Default shows `us-central1`; use `--region` (repeatable) or `--all-regions`.
- Every row carries `source_url` + `fetched_at`, and the table prints a `Source:` footer —
  **share that link so the user can open the page and eye-check the numbers themselves.**
- `price_type` values: `on-demand, spot, flex, calendar, cud-1y, cud-3y` (compute/TPU).
  Unrecognized columns keep the page's own label and are flagged `"raw": true`.
- `--verify` cross-checks against the Billing Catalog API (needs a gcloud token); off by default.
- No credentials required for normal use.
