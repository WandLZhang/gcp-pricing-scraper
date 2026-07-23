---
name: gcp-pricing
description: Get live Google Cloud pricing for ANY product (VMs, GPUs, TPUs, BigQuery, storage, Lustre, Spanner, ...). Use whenever asked for a GCP price, cost, rate, or $/hr - the official pricing pages are JS-rendered so WebFetch fails; this scrapes their embedded data instead.
---

# gcp-pricing

A zero-auth CLI that returns current Google Cloud pricing by scraping the official
`cloud.google.com/**/pricing` pages (their numbers are embedded in the page; WebFetch
only sees the empty shell). All regions, every column the page shows.

## Use it

Run the CLI with your Bash tool and read stdout:

```
gcp-pricing <product|url> [--filter TEXT ...] [--json]
```

Examples:
- `gcp-pricing accelerator --filter h200 --filter netherlands`
- `gcp-pricing gpu --filter h100 --json`
- `gcp-pricing tpu --filter Trillium`  (TPU incl. Ironwood/v7 + Trillium, absent from the billing API)
- `gcp-pricing bigquery --filter slot`
- `gcp-pricing storage --filter rapid`
- `gcp-pricing https://cloud.google.com/spanner/pricing`  (any page by URL)

Known names: `vms, accelerator, gpu, tpu, storage, lustre, parallelstore, bigquery,
cloud-run, gke, spanner, cloud-sql, vertex-ai` (plus aliases). Anything else: pass the
pricing URL directly, or the tool will pattern-guess it.

## How to read the output - IMPORTANT

The tool does **no interpretation**. It returns the page's own **column headers** and the
**raw cell strings, verbatim**, as one or more `sheets` of `{headers, rows}`. YOU read the
table: find the header for the price type you want, read the cell beneath it. A cell may be
`"-"` (not offered - e.g. H200 has no On-Demand in some regions) or `"$X / 1 hour"`; the
dash holds its column slot so nothing shifts.

This is deliberate. Pricing pages are dynamic and vary wildly (regions as rows or as
columns; different column sets per product), so any canonical labeling on the tool's side
would be brittle and could silently mislabel. The LLM reading the table is the robust
interpreter - the tool's only job is faithful extraction.

- Every sheet prints a `Source (open to verify)` URL - **share it so the user can open the
  page and eye-check the numbers.**
- `--filter` is a plain substring match over a whole row; repeat for AND
  (`--filter h200 --filter netherlands`). All regions/columns are included by default.
- `--json` emits the raw sheets for programmatic reasoning.
- No credentials required, ever.
