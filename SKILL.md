---
name: gcp-pricing
description: Get live Google Cloud pricing, terms, and eligibility rules for ANY product (VMs, GPUs, TPUs, BigQuery, storage, Spark, Vertex/Agent Platform, support tiers). Use whenever asked for a GCP price, cost, rate, $/hr, minimum, or discount eligibility - the official pages are JS-rendered so WebFetch returns an empty shell.
---

# gcp-pricing

Captures a Google Cloud pricing page **whole** and writes it to a file you can grep. No auth.
No interpretation. Nothing dropped.

```
gcp-pricing <product|url> [--filter TEXT ...] [--catalog] [--json] [--limit N]
```

Every run writes the complete capture to `/tmp/gcp-pricing/<page>.txt` and prints the path.
`--filter` only controls what is echoed to stdout — **the file always has everything.**

The capture holds, in order:
1. the whole page as readable markdown — headings, prose, lists, and **every** table
   (including tables with no `$` in them: minimum durations, free tiers, eligibility lists);
2. every row from the page's inline JSON blob, tab-separated, one per line — the only source
   of non-default regions.

## Work the file, not the tool

The general-purpose page captures to ~6.7 MB / 9,364 region rows. Don't ask the tool to
find things for you — grep the capture:

```bash
gcp-pricing general-purpose --filter "zzz"          # capture, echo nothing
F=/tmp/gcp-pricing/cloud.google.com_products_compute_pricing_general-purpose*.txt
grep -P '^Northern Virginia' $F | grep -oP '\S+-8\t8\t16 GiB\t\$[\d.]+' | sort -t'$' -k2 -g
```

That returns every 8 vCPU / 16 GiB shape in us-east4, cheapest first. Which is the query
that matters.

## The one rule: never strip context off a number

Every wrong number traced back to something that removed a value's coordinates:

| What stripped it | What was lost |
|---|---|
| a `$`-gate in the extractor | 5 tables, incl. minimum storage durations |
| a block-picker choosing "the" table | 13 of 14 machine families |
| WebFetch | whole tables |
| filtering by a SKU name chosen in advance | the cheaper candidate |
| `grep -oP` | the region prefix — a DCU rate was read from an arbitrary region |
| `head -2` | the 40 other matching regions, which would have shown the query was ambiguous |

So:

- **Grep whole lines. Never `-o`.** Every captured line already carries its region, item,
  unit and value. A fragment does not, and a fragment that looks like an answer is how a
  wrong number ships silently.
- **Never `head` a result you are about to quote.** Count first (`| wc -l`). If a query for
  one number returns many rows, the query is under-specified — that is the signal, and
  truncating destroys it.
- **More than one distinct value for what should be one number = stop.** Pin the missing
  coordinate (usually region) and re-run.
- **When a number matters, read its raw line.** Not a summary, not a rendered table — the
  line in the capture file.

Pages also print every rate twice, hourly and monthly at exactly x730. If a value needs
confirming, grep both lines and look at them. Do not build a reconciler; that is more
processing, and processing is what caused all of this.

## Operating rules

These exist because each one was violated in a real analysis and cost a wrong number.

- **Query by requirement, never by name.** List every candidate meeting the spec and sort by
  price *before* choosing. If a SKU name appears in your query before the spec does, stop —
  that is how `n4a-highcpu-8` ($0.25984) got missed in favour of `c4a-highcpu-8` ($0.30304).
- **A page omission is not a product limit.** Pages and the Billing Catalog API each omit
  what the other has. Before writing "not available", check `--catalog` and
  `gcloud compute accelerator-types list --filter="zone~REGION"`. The Agent Platform page's
  us-east4 table lists no T4; the catalog prices it at $0.444/hr.
- **Do not inherit a third party's service mapping.** Verify the engine matches before
  pricing their named target. AWS Glue runs Spark; Dataflow runs Beam — that mapping was a
  rewrite, not a migration, and priced the wrong service.
- **Sweep every dimension per line item**: region · machine family or storage class ·
  commitment (on-demand / Flex CUD / Resource CUD) · tier · batch / Spot. Storage class alone
  was worth −$512/mo; the model ladder −$490/mo.
- **Never state a rate from memory** when a page exists. Support tiers were written from
  recall and came out as the wrong product's structure.
- **When the tool falls short, ask for the page immediately.** One turn: "paste me X." Do not
  burn turns on WebFetch (it summarizes and drops tables) or assert and hope.
- **Re-grep your own artifact for superseded strings** after every correction round.

## Second source

```
gcp-pricing notebooks --catalog --filter "gpu" --filter "t4 in us-east4"
```

Queries the Cloud Billing Catalog API via `gcloud auth print-access-token`. Known service
IDs are in `registry.py` (Notebooks `D73B-5EEA-8215`, Compute Engine `6F81-5844-456A`);
anything else is found by scanning `displayName`. Substring filters are literal — `t4` also
matches `us-east4`, so filter on `t4 in us-east4`.

## Product names

`vms · general-purpose · accelerator · gpu · tpu · storage · lustre · parallelstore ·
bigquery · cloud-run · gke · spanner · cloud-sql · vertex-ai · generative-ai ·
managed-spark · dataflow · support · sud` (plus aliases: `dataproc`→`managed-spark`,
`agent-platform`/`workbench`→`vertex-ai`, `gemini`/`claude`→`generative-ai`, …).

Anything else: pass the URL. `docs.cloud.google.com` pages work too — that is where
eligibility rules live (e.g. `sud` → sustained use discounts).

## Develop

```bash
python tests/capture_fixtures.py     # real page captures, gitignored
PYTHONPATH=. python3 -m pytest -q
```
