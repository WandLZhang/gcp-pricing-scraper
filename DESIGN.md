# gcp-pricing — design spec

**Status:** draft for review · **Date:** 2026-07-23
**One line:** An auth-free CLI (wrapped as a thin per-coder "skill") that returns live pricing for *any* Google Cloud product by scraping its official `cloud.google.com/**/pricing` page — because those pages embed complete, all-region pricing data that WebFetch/summarizers silently drop.

---

## 1. Problem & root cause

Claude Code (and the dev-knowledge MCP) can't return GCP accelerator/TPU prices. Root cause, verified: the pricing pages render tables client-side, and WebFetch pipes a 2–6 MB page through a summarizer that discards the tables. The numbers **are** in the page — as visible `<table>`s and, for compute, as a large inline JSON blob holding every region. No official GCP pricing MCP exists; the sanctioned programmatic source (Billing Catalog API) needs a token **and** is incomplete (it lacks Ironwood/v7 TPUs entirely, files current TPUs under Compute Engine, and gives per-chip only).

## 2. What we proved (live, browserless, no auth)

- Numbers are embedded in raw HTML. Two extraction paths cover every page tested:
  - **Visible tables** (TPU, storage, Lustre, Parallelstore) → BeautifulSoup/lxml.
  - **Embedded JSON blob** (compute families, BigQuery) → an inline `[[...]]` array, `json.loads`-parseable, holding all regions + all prices.
- Coverage confirmed: general-purpose VMs (47 regions / 177k prices), compute-optimized (45), GPUs per-chip (41), accelerator-optimized per-VM (45), TPU (incl. **Ironwood/v7 + Trillium**, absent from the API), BigQuery (56 regions / 38 tables), Cloud Storage **incl. Rapid Storage**, Managed Lustre (`/products/managed-lustre/pricing`), Parallelstore.
- The mechanism is **product-agnostic**: every `cloud.google.com/**/pricing` page follows this pattern, so the tool generalizes to VMs, BigQuery, and specialty knobs — not just accelerators.

## 3. Architecture — one engine, three layers

`gcp_pricing.py` (stdlib + `beautifulsoup4` + `lxml` only; **no pandas at runtime**, for mobile/Cline portability; **no credentials**).

1. **Resolver** `product|url → pricing URL(s)`
   - Curated **registry** of common products → canonical URL(s). Hubs expand to subpages (e.g. `vms` → general-purpose / compute-optimized / memory-optimized / storage-optimized / accelerator-optimized; `gpu` → per-VM + per-chip pages).
   - Not in registry → probe URL patterns `/{p}/pricing`, `/products/{p}/pricing`.
   - Still unresolved → return a clear "pass the pricing URL directly" message. Discovery (WebSearch / dev-knowledge MCP) is the *calling agent's* job, not the CLI's; the agent re-invokes with the URL. This is how "anything" stays guaranteed without baking network deps into the script.

2. **Extractor** (deterministic, structural — no regex on prose)
   - `visible_tables`: walk `<table>` → row/col matrices.
   - `embedded_blob`: locate the inline region-labeled JSON array → `json.loads` → walk to `(region, item, price_column)` records.
   - Emits normalized `{product, url, source, regions[], rows[], raw_tables[]}`.

3. **Labeler**
   - **Registry products:** apply a baked `schema.json` (column→price-type maps: on-demand / spot / 1y-CUD / 3y-CUD / flex / calendar). Authored once by inspecting the pages during build (by the coding agent — **no LLM API call at build or runtime**). This is where the "let an LLM read the labels, don't regex them" rule is honored: semantic column mapping was done by an LLM, then frozen.
   - **Unknown products:** return structured-but-unlabeled tables/blob; the calling agent interprets. Optional `--llm-label` only if the user wires creds later.
   - **Layout-change guard:** each schema stores a header fingerprint; on mismatch the tool warns and falls back to raw output rather than emit mislabeled prices.

4. **Optional `--verify`** (the *only* path that touches a token): cross-check scraped numbers against the Billing Catalog API, flag page-vs-API drift, add Flex/Calendar modes. Off by default.

## 4. CLI

```
gcp-pricing <product|url> [--region R | --all-regions]
                          [--table | --json | --raw]
                          [--filter TEXT] [--verify] [--debug]
```
Examples: `gcp-pricing accelerator --all-regions --json` · `gcp-pricing tpu` ·
`gcp-pricing bigquery --filter slots` · `gcp-pricing storage --filter rapid` ·
`gcp-pricing https://cloud.google.com/spanner/pricing`

Default output = readable table; `--json` for tooling; `--raw` dumps every extracted table (arbitrary products / debugging). **Always live-fetch** (page = source of truth; ~2–3 s). No cache — a stale Spot price in a customer quote is worse than a 2 s wait. A hub product like `vms --all-regions` fans its family subpages out concurrently.

## 5. Data integrity (per house rules)

Real data only — never fabricate a price. Unparseable page → say so, exit non-zero. `--debug` logs the full extracted payload. `--verify` surfaces real discrepancies. Prices are quoted with their source URL + fetch timestamp so a customer number is always traceable.

## 6. Packaging

Shared artifact: `gcp_pricing.py` + `schema.json`. Personal install: `~/.claude/skills/gcp-pricing/` (engine + `SKILL.md`). Each of the four setup repos already has a `setup.sh` + coder dirs, so each `setup.sh` installs the engine to `~/.local/bin/gcp-pricing` (on PATH) and drops that coder's thin instruction file:

| Repo | Instruction wrapper |
|---|---|
| `claude-code-setup` | `claude-code/skills/gcp-pricing/SKILL.md` (+ CLAUDE.md note) |
| `antigravity-setup` | rule/workflow in `config-files/` |
| `cline-mobile-config` | rule in `rules/` |
| `GPS-AI-Infra-Onboarding-Workshop/01-foundational-tools/agentic-coder-setup` | note under `cli-agent/` and `cline/` |

The wrapper is ~5 lines: "To get live GCP pricing for any product, run `gcp-pricing <product> [flags]` — scrapes the official page, no auth."

## 7. Non-goals

No MCP server (a shell CLI is the whole substance). No runtime credentials in the default path. No headless browser. No hardcoded prices. Not a cost *calculator* (no usage-quantity math) — it returns rates; the agent does any arithmetic.

## 8. Decisions (resolved)

1. Command name: **`gcp-pricing`**.
2. Registry v1 seed: VMs, GPU (per-VM + per-chip), TPU, Storage + Rapid, Lustre, Parallelstore, BigQuery, Cloud Run, GKE, Spanner, Cloud SQL, Vertex AI. Anything else works via URL or pattern-probe.
3. **No cache** — always live-fetch (see §4).
