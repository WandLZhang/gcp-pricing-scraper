# gcp-pricing

Raw Google Cloud pricing for **any** product, scraped from the official
`cloud.google.com/**/pricing` pages. Zero auth, zero interpretation.

Those pages render their tables client-side, so `WebFetch` (and most agents) see an empty
shell. The numbers are actually embedded in the page — as visible `<table>`s and, for
compute/BigQuery, as a large inline JSON blob covering every region. This tool extracts
them and hands over the page's **own column headers + raw cell strings, verbatim**. It does
**not** normalize, relabel, or align anything — pricing pages are dynamic and vary wildly,
so the reader (you, or an LLM agent) interprets the table. That's what keeps it from
silently mislabeling when Google reshapes a page.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/WandLZhang/gcp-pricing-scraper/main/install.sh | bash
```

Installs the `gcp-pricing` CLI onto your PATH (isolated via pipx or a venv; falls back to
`pip --user`). Only deps are `beautifulsoup4` + `lxml`. If Claude Code is present, it also
drops `SKILL.md` into `~/.claude/skills/` so the agent auto-discovers the tool.

Or with pipx directly:

```bash
pipx install "git+https://github.com/WandLZhang/gcp-pricing-scraper"
```

## Use

```bash
gcp-pricing <product|url> [--filter TEXT ...] [--json]
```

Examples:

```bash
gcp-pricing accelerator --filter h200 --filter netherlands
gcp-pricing gpu --filter h100 --json
gcp-pricing tpu --filter Trillium          # incl. Ironwood/v7 + Trillium (absent from billing API)
gcp-pricing bigquery --filter slot
gcp-pricing https://cloud.google.com/spanner/pricing
```

Known names: `vms, accelerator, gpu, tpu, storage, lustre, parallelstore, bigquery,
cloud-run, gke, spanner, cloud-sql, vertex-ai` (plus aliases). Anything else: pass the
pricing URL, or let the tool pattern-guess it.

## How to read the output

Output is one or more `sheets` of `{headers, rows}` — the page's own columns and raw cells.
Find the header for the price type you want, read the cell beneath it. A cell may be `"-"`
(not offered — e.g. H200 has no On-Demand in some regions; the dash holds its column so
nothing shifts) or `"$X / 1 hour"`. `--filter` is a plain substring match over a whole row
(repeat for AND). Every sheet prints a `Source (open to verify)` URL — open it to eye-check.

## Develop

```bash
pip install -e .
python -m pytest -m "not live"     # fast, uses captured fixtures
python -m pytest -m live           # hits cloud.google.com
python tests/capture_fixtures.py   # refresh fixtures (gitignored)
```
