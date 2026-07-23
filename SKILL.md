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

- **Raw numbers, any structure.** Every row carries the page's own `column` label and its
  raw `value` string (e.g. `"$93.40 / 1 hour"`) **verbatim — these are authoritative.**
  `price_type`, `price`, `unit` are best-effort conveniences layered on top; if they ever
  disagree with `value`, trust `value`. This is deliberate: pages differ wildly (some list
  regions as rows, some as columns), so the tool surfaces the real cells and lets *you*
  interpret rather than over-normalizing and risking a wrong label.
- Default returns **all regions — nothing is hidden**. Narrow with `--region` (repeatable;
  matches a region code, a region name, or a column like `Europe`) or `--filter`.
- Default output is a table; add `--json` for structured rows (preferred for reasoning).
- Every row carries `source_url` + `fetched_at`, and the table prints a `Source:` footer —
  **share that link so the user can open the page and eye-check the numbers themselves.**
- `--verify` cross-checks against the Billing Catalog API (needs a gcloud token); off by default.
- No credentials required for normal use.
