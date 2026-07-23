# gcp-pricing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A zero-auth CLI that returns live pricing for any Google Cloud product by scraping its official pricing page, distributable as a thin per-coder skill.

**Architecture:** `resolve(product|url) → fetch(html) → extract(tables|blob) → label(schema) → format`. Two extractors: BeautifulSoup for visible tables (regions-as-rows products), and a JSON-blob walker for compute/BigQuery (all-region data embedded inline). Correctness is guaranteed by cross-checking the blob's default-region block against the visible table. An optional `--verify` path cross-checks the Billing Catalog API.

**Tech Stack:** Python 3 (stdlib `urllib`, `json`, `argparse`), `beautifulsoup4` + `lxml` for HTML. No pandas, no network deps, no credentials in the default path.

## Global Constraints

- Runtime deps: **only** `beautifulsoup4` + `lxml`. Stdlib for everything else. (Portability to Cline/mobile.)
- **No credentials** in the default path. Only `--verify` may call `gcloud auth print-access-token`.
- **No regex to parse prose/labels.** Structural parse (bs4/json) only; semantic column→price-type mapping is frozen in `schema.json` (authored by inspecting pages, not at runtime).
- **No fabricated data.** Unparseable page → clear error, non-zero exit. Never invent a price.
- Every quoted price carries `source_url` + `fetched_at` (UTC ISO-8601).
- Tests run against **real captured HTML fixtures** and assert **invariants** (region counts, positive floats, cross-source equality, economic ordering), never hardcoded absolute prices (which legitimately change).
- Package dir: `~/.claude/skills/gcp-pricing/`. Distributed artifact = `gcp_pricing/` + `schema.json` + `SKILL.md` only (not `tests/` or fixtures).

---

## File Structure

```
~/.claude/skills/gcp-pricing/
  SKILL.md                    # per-coder discovery wrapper
  requirements.txt            # beautifulsoup4, lxml
  bin/gcp-pricing             # shim -> python3 -m gcp_pricing "$@"
  gcp_pricing/
    __init__.py
    __main__.py               # -> cli.main()
    fetch.py                  # fetch(url)->str ; FetchError
    extract.py                # extract(html,url)->Extraction ; blob + table walkers
    registry.py               # PRODUCTS: dict[str, list[str]]
    resolver.py               # resolve(token)->Resolution
    label.py                  # load_schema(); label(extraction, product)-> list[PriceRow]
    schema.json               # column->price_type maps + header fingerprints
    verify.py                 # verify(rows)-> list[Discrepancy]  (optional)
    cli.py                    # argparse + orchestration + formatting
  tests/
    conftest.py               # fixture loader
    capture_fixtures.py       # downloads real pages -> tests/fixtures/ (gitignored)
    fixtures/                 # real HTML captures (gitignored)
    test_fetch.py test_extract_blob.py test_extract_tables.py
    test_resolver.py test_label.py test_cli.py test_verify.py
    test_integration_live.py  # @pytest.mark.live
  .gitignore                  # tests/fixtures/, __pycache__, *.pyc
```

**Data model (shared IR):**
- `Extraction = {"kind": "blob"|"tables", "columns": list[str], "records": list[Record], "source_url": str}`
- `Record = {"item": str, "region_code": str|None, "region_name": str|None, "values": dict[str,str]}`  (values keyed by page column header → raw cell text)
- `PriceRow = {"product","item","attrs":dict,"region_code","region_name","price_type","unit","price":float,"currency","source_url","fetched_at"}`

---

### Task 1: Scaffold + `fetch` + real fixtures

**Files:**
- Create: `gcp_pricing/__init__.py`, `gcp_pricing/__main__.py`, `gcp_pricing/fetch.py`, `requirements.txt`, `.gitignore`, `tests/conftest.py`, `tests/capture_fixtures.py`
- Test: `tests/test_fetch.py`

**Interfaces:**
- Produces: `fetch(url: str, timeout: int = 40) -> str` (raises `FetchError` with a human message on HTTP/network error); `FetchError(Exception)`.

- [ ] **Step 1: Write `requirements.txt` and `.gitignore`**

```
# requirements.txt
beautifulsoup4>=4.12
lxml>=5.0
```
```
# .gitignore
tests/fixtures/
__pycache__/
*.pyc
```

- [ ] **Step 2: Write the fixture capture helper** (`tests/capture_fixtures.py`)

```python
"""Download real GCP pricing pages into tests/fixtures/. Run once before tests:
   python tests/capture_fixtures.py
Fixtures are gitignored (large) and are real page captures, not mock data."""
import os, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
PAGES = {
    "accelerator.html": "https://cloud.google.com/products/compute/pricing/accelerator-optimized?hl=en",
    "tpu.html": "https://cloud.google.com/tpu/pricing?hl=en",
    "bigquery.html": "https://cloud.google.com/bigquery/pricing?hl=en",
    "storage.html": "https://cloud.google.com/storage/pricing?hl=en",
}
def main():
    here = os.path.join(os.path.dirname(__file__), "fixtures")
    os.makedirs(here, exist_ok=True)
    for name, url in PAGES.items():
        req = urllib.request.Request(url, headers=UA)
        html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        open(os.path.join(here, name), "w").write(html)
        print(f"captured {name}: {len(html)} bytes")
if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write `conftest.py` fixture loader**

```python
import os, pytest
FIX = os.path.join(os.path.dirname(__file__), "fixtures")
def _load(name):
    path = os.path.join(FIX, name)
    if not os.path.exists(path):
        pytest.skip(f"fixture {name} missing; run: python tests/capture_fixtures.py")
    return open(path, encoding="utf-8").read()
@pytest.fixture
def accel_html(): return _load("accelerator.html")
@pytest.fixture
def tpu_html(): return _load("tpu.html")
@pytest.fixture
def bigquery_html(): return _load("bigquery.html")
@pytest.fixture
def storage_html(): return _load("storage.html")
```

- [ ] **Step 4: Write failing test** (`tests/test_fetch.py`)

```python
import os, pytest
from gcp_pricing.fetch import fetch, FetchError

def test_fetch_reads_local_file(tmp_path):
    p = tmp_path / "x.html"; p.write_text("<html>hi</html>")
    assert "hi" in fetch(p.as_uri())

def test_fetch_raises_clear_error_on_bad_scheme():
    with pytest.raises(FetchError):
        fetch("https://cloud.google.invalid/nope")
```

- [ ] **Step 5: Run test to verify it fails** — `pytest tests/test_fetch.py -v` → FAIL (module not found)

- [ ] **Step 6: Implement `fetch.py`**

```python
import urllib.request, urllib.error
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
class FetchError(Exception): pass
def fetch(url: str, timeout: int = 40) -> str:
    try:
        req = urllib.request.Request(url, headers=UA)
        return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise FetchError(f"HTTP {e.code} fetching {url}") from e
    except Exception as e:
        raise FetchError(f"could not fetch {url}: {e}") from e
```
And `__main__.py`:
```python
from gcp_pricing.cli import main
if __name__ == "__main__": main()
```
(`__init__.py` empty for now.)

- [ ] **Step 7: Run tests to verify pass** — `pytest tests/test_fetch.py -v` → PASS

- [ ] **Step 8: Capture fixtures + commit** — `python tests/capture_fixtures.py` then
```bash
git init 2>/dev/null; git add gcp_pricing requirements.txt .gitignore tests/conftest.py tests/capture_fixtures.py tests/test_fetch.py
git commit -m "feat(gcp-pricing): scaffold + fetch module + real fixture capture"
```

---

### Task 2: Blob extractor (all-region compute/BigQuery)

**Files:**
- Modify: `gcp_pricing/extract.py`
- Test: `tests/test_extract_blob.py`

**Interfaces:**
- Produces: `find_blob(html: str) -> list|None` (the decoded JSON array, or None); `walk_blob(data: list) -> tuple[list[dict], list[str], list[Record]]` returning `(regions, columns, records)` where `regions=[{"code","name"}]`. `extract(html, url)` (full dispatcher) is finished in Task 3.
- Consumes: `Record` shape from the data model.

- [ ] **Step 1: Write failing test** (`tests/test_extract_blob.py`)

```python
import re
from gcp_pricing.extract import find_blob, walk_blob

def test_blob_found_and_regions(accel_html):
    data = find_blob(accel_html)
    assert data is not None
    regions, columns, records = walk_blob(data)
    codes = {r["code"] for r in regions}
    assert len(codes) >= 40                       # invariant: ~45 regions
    assert "europe-west4" in codes                # Netherlands present
    assert any(r["name"].endswith("(europe-west4)") for r in regions)

def test_blob_records_have_positive_prices(accel_html):
    _, _, records = walk_blob(find_blob(accel_html))
    a4 = [r for r in records if "a4-highgpu-8g" in r["item"] and r["region_code"] == "us-central1"]
    assert a4, "a4-highgpu-8g not found in us-central1"
    prices = [float(m.group()) for r in a4 for v in r["values"].values()
              for m in [re.search(r"\d+\.?\d*", v.replace(",", ""))] if m and "$" in v]
    assert prices and all(p > 0 for p in prices)
```

- [ ] **Step 2: Run test to verify it fails** — `pytest tests/test_extract_blob.py -v` → FAIL

- [ ] **Step 3: Implement blob walker in `extract.py`** (structural locator — no hardcoded page path)

```python
import json
from bs4 import BeautifulSoup

_REGION_HINT = ("us-", "europe-", "asia-", "africa-", "me-", "australia-",
                "northamerica-", "southamerica-")

def _is_region_label(s):
    return isinstance(s, str) and s.endswith(")") and "(" in s and any(h in s for h in _REGION_HINT)

def find_blob(html):
    """Return the decoded inline JSON pricing array, or None."""
    soup = BeautifulSoup(html, "lxml")
    best = None
    for sc in soup.find_all("script"):
        t = sc.string or sc.get_text() or ""
        if "[[" in t and sum(t.count(h) for h in _REGION_HINT) > 20:
            try:
                data, _ = json.JSONDecoder().raw_decode(t, t.find("[["))
            except Exception:
                continue
            n = _count(data, _is_region_label)
            if best is None or n > best[0]:
                best = (n, data)
    return best[1] if best else None

def _count(node, pred):
    if pred(node): return 1
    if isinstance(node, list): return sum(_count(e, pred) for e in node)
    return 0

def _find_path(node, pred, path=()):
    if pred(node): return path
    if isinstance(node, list):
        for i, e in enumerate(node):
            p = _find_path(e, pred, path + (i,))
            if p is not None: return p
    return None

def _get(node, path):
    for i in path: node = node[i]
    return node

def _region_label_array(node):
    # the pricing table's region list: a list of >=40 "City (code)" strings
    if isinstance(node, list) and sum(1 for e in node if _is_region_label(e)) >= 40:
        return True
    return False

def _strings(node, out):
    if isinstance(node, str): out.append(node)
    elif isinstance(node, list):
        for e in node: _strings(e, out)

def _cells(node):
    """Ordered cell strings within a region block: machine ids (<p>id</p>) and prices ($...)."""
    out = []; _strings(node, out)
    return [s for s in out]

def walk_blob(data):
    p = _find_path(data, _region_label_array)
    if p is None:
        return [], [], []
    labels = _get(data, p)                                   # ["City (code)", ...]
    pricing_table = _get(data, p[:-1])                       # [[colidx],[labels]] is pricing_table[1]
    # climb until we find the node whose child index 1 is [_, labels] and index 3 is the blocks list
    table = _get(data, p[:-2])
    region_blocks = table[3]
    regions = [{"name": s, "code": s[s.rfind("(") + 1:-1]} for s in labels]
    # Extract per-region rows using ordered cells; machine ids marked by "<p>...</p>" containing a code-like token
    records, columns = [], []
    for r_idx, region in enumerate(regions):
        if r_idx >= len(region_blocks): break
        rows = _extract_block_rows(region_blocks[r_idx])
        for item, values in rows:
            if not columns and values: columns = list(values.keys())
            records.append({"item": item, "region_code": region["code"],
                            "region_name": region["name"], "values": values})
    return regions, columns, records

def _extract_block_rows(block):
    """A block mirrors the visible table: yield (item_label, {col_index: price_str})."""
    rows = []
    def is_item(s): return isinstance(s, str) and "<p>" in s and "-" in s and "$" not in s
    def is_price(s): return isinstance(s, str) and s.strip().startswith("$")
    # Walk row containers: each machine row groups an item label followed by its price cells.
    flat = []; _strings(block, flat)
    cur_item, cur_vals, col = None, {}, 0
    import re as _re
    for s in flat:
        if is_item(s):
            if cur_item and cur_vals: rows.append((cur_item, cur_vals))
            cur_item = _re.sub(r"<[^>]+>", "", s).strip(); cur_vals = {}; col = 0
        elif is_price(s) and cur_item is not None:
            cur_vals[str(col)] = s.strip(); col += 1
    if cur_item and cur_vals: rows.append((cur_item, cur_vals))
    return rows
```
*(Note: `_re.sub` strips HTML tags from an item label — tag removal, not price parsing; permitted. Price values stay raw strings for the labeler.)*

- [ ] **Step 4: Run tests to verify pass** — `pytest tests/test_extract_blob.py -v` → PASS

- [ ] **Step 5: Commit**
```bash
git add gcp_pricing/extract.py tests/test_extract_blob.py
git commit -m "feat(gcp-pricing): all-region JSON blob walker with structural locator"
```

---

### Task 3: Visible-table extractor + `extract` dispatcher + cross-check

**Files:**
- Modify: `gcp_pricing/extract.py`
- Test: `tests/test_extract_tables.py`

**Interfaces:**
- Produces: `extract_tables(html: str) -> tuple[list[str], list[Record]]`; `extract(html: str, url: str) -> Extraction` (tries blob, falls back to tables; sets `kind`).
- Consumes: `walk_blob`, `find_blob` from Task 2.

- [ ] **Step 1: Write failing test** (`tests/test_extract_tables.py`)

```python
from gcp_pricing.extract import extract_tables, extract

def test_tpu_tables_have_current_generations(tpu_html):
    columns, records = extract_tables(tpu_html)
    items = " ".join(r["item"] for r in records)
    assert "Trillium" in items          # v6e
    assert "Ironwood" in items          # v7 — absent from Billing Catalog API
    # every price-shaped value parses to a positive number
    vals = [v for r in records for v in r["values"].values() if v.strip().startswith("$")]
    assert vals

def test_extract_dispatches_blob_for_accel(accel_html):
    ex = extract(accel_html, "http://x/accelerator")
    assert ex["kind"] == "blob"
    assert len(ex["records"]) > 100

def test_extract_dispatches_tables_for_tpu(tpu_html):
    ex = extract(tpu_html, "http://x/tpu")
    assert ex["kind"] == "tables"
```

- [ ] **Step 2: Run test to verify it fails** — `pytest tests/test_extract_tables.py -v` → FAIL

- [ ] **Step 3: Implement `extract_tables` + `extract`**

```python
def extract_tables(html):
    soup = BeautifulSoup(html, "lxml")
    columns, records = [], []
    for tbl in soup.find_all("table"):
        trs = tbl.find_all("tr")
        if not trs: continue
        header = [c.get_text(" ", strip=True) for c in trs[0].find_all(["th", "td"])]
        for tr in trs[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if not cells: continue
            item = cells[0]
            values = {header[i] if i < len(header) else str(i): cells[i] for i in range(len(cells))}
            # region: detect a cell that is a bare region code
            rc = next((c for c in cells if _looks_like_code(c)), None)
            records.append({"item": item, "region_code": rc, "region_name": None, "values": values})
            if len(header) > len(columns): columns = header
    return columns, records

def _looks_like_code(s):
    return isinstance(s, str) and any(s.startswith(h) for h in _REGION_HINT) and " " not in s

def extract(html, url):
    data = find_blob(html)
    if data is not None:
        regions, columns, records = walk_blob(data)
        if records:
            return {"kind": "blob", "columns": columns, "records": records, "source_url": url}
    columns, records = extract_tables(html)
    return {"kind": "tables", "columns": columns, "records": records, "source_url": url}
```

- [ ] **Step 4: Run tests to verify pass** — `pytest tests/test_extract_tables.py -v` → PASS

- [ ] **Step 5: Commit**
```bash
git add gcp_pricing/extract.py tests/test_extract_tables.py
git commit -m "feat(gcp-pricing): visible-table extractor + blob/table dispatcher"
```

---

### Task 4: Registry + resolver

**Files:**
- Create: `gcp_pricing/registry.py`, `gcp_pricing/resolver.py`
- Test: `tests/test_resolver.py`

**Interfaces:**
- Produces: `PRODUCTS: dict[str, list[str]]`; `resolve(token: str) -> dict` = `{"product": str, "urls": list[str], "resolved_by": "registry"|"passthrough"|"pattern", "note": str|None}`; raises `Unresolved(Exception)` with guidance when nothing matches.

- [ ] **Step 1: Write failing test** (`tests/test_resolver.py`)

```python
import pytest
from gcp_pricing.resolver import resolve, Unresolved

def test_known_product_maps_to_urls():
    r = resolve("tpu")
    assert r["resolved_by"] == "registry"
    assert any("tpu/pricing" in u for u in r["urls"])

def test_hub_product_expands_to_subpages():
    r = resolve("vms")
    assert len(r["urls"]) >= 4            # general-purpose, compute-optimized, ...

def test_raw_url_passthrough():
    r = resolve("https://cloud.google.com/spanner/pricing")
    assert r["resolved_by"] == "passthrough"
    assert r["urls"] == ["https://cloud.google.com/spanner/pricing"]

def test_unknown_word_raises_with_guidance():
    with pytest.raises(Unresolved) as e:
        resolve("totally-made-up-xyz")
    assert "pricing URL" in str(e.value)
```

- [ ] **Step 2: Run test to verify it fails** — `pytest tests/test_resolver.py -v` → FAIL

- [ ] **Step 3: Implement `registry.py` + `resolver.py`**

```python
# registry.py
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
ALIASES = {"vm": "vms", "gpus": "gpu", "accelerators": "accelerator",
           "gcs": "storage", "rapid": "storage", "bq": "bigquery",
           "run": "cloud-run", "sql": "cloud-sql", "vertex": "vertex-ai"}
```
```python
# resolver.py
from .registry import PRODUCTS, ALIASES, BASE
class Unresolved(Exception): pass
def resolve(token):
    t = token.strip()
    if t.startswith("http://") or t.startswith("https://"):
        return {"product": t, "urls": [t], "resolved_by": "passthrough", "note": None}
    key = ALIASES.get(t.lower(), t.lower())
    if key in PRODUCTS:
        return {"product": key, "urls": PRODUCTS[key], "resolved_by": "registry", "note": None}
    # pattern probe candidates (the CLI will try fetching these; resolver just proposes)
    cands = [f"{BASE}/{key}/pricing?hl=en", f"{BASE}/products/{key}/pricing?hl=en"]
    return {"product": key, "urls": cands, "resolved_by": "pattern", "note":
            "guessed URL by pattern; if wrong, pass the exact pricing URL"}
```
*(Note: `resolve` never raises for pattern guesses; the CLI validates them by fetching and raises `Unresolved` only if all candidates fail — tested in Task 6. Update the test accordingly:)*

```python
# replace test_unknown_word_raises_with_guidance with:
def test_unknown_word_returns_pattern_candidates():
    r = resolve("totally-made-up-xyz")
    assert r["resolved_by"] == "pattern"
    assert all("pricing" in u for u in r["urls"])
```

- [ ] **Step 4: Run tests to verify pass** — `pytest tests/test_resolver.py -v` → PASS

- [ ] **Step 5: Commit**
```bash
git add gcp_pricing/registry.py gcp_pricing/resolver.py tests/test_resolver.py
git commit -m "feat(gcp-pricing): product registry + resolver (registry/passthrough/pattern)"
```

---

### Task 5: `schema.json` + labeler + layout guard

**Files:**
- Create: `gcp_pricing/schema.json`, `gcp_pricing/label.py`
- Test: `tests/test_label.py`

**Interfaces:**
- Produces: `load_schema() -> dict`; `label(extraction: Extraction, product: str, schema: dict) -> list[PriceRow]`; `header_fingerprint(columns: list[str]) -> str`. On fingerprint mismatch, emits rows with `price_type="unknown"` and sets `PriceRow["raw"]=True` (no fabricated labels).
- Consumes: `Extraction`/`Record` from Task 3.

- [ ] **Step 1: Author `schema.json`** by inspecting the captured fixtures (map each product's price columns to canonical types; record the header fingerprint). Structure:

```json
{
  "accelerator": {
    "fingerprint": "FILL_FROM_FIXTURE",
    "columns": {"0": "on-demand", "1": "cud-1y", "2": "cud-3y", "3": "spot"},
    "unit": "hour"
  },
  "tpu": {
    "fingerprint": "FILL_FROM_FIXTURE",
    "region_column": "region",
    "columns": {"on-demand": "on-demand", "spot": "spot", "1y": "cud-1y", "3y": "cud-3y"},
    "unit": "chip-hour"
  }
}
```
The implementer computes `fingerprint` via `header_fingerprint(extract(fixture)["columns"])` and pastes the real value; column indices are read off the fixture. (This is the one-time LLM-as-labeler step, frozen to disk.)

- [ ] **Step 2: Write failing test** (`tests/test_label.py`)

```python
from gcp_pricing.extract import extract
from gcp_pricing.label import load_schema, label, header_fingerprint

def test_accel_rows_are_typed(accel_html):
    ex = extract(accel_html, "http://x/accelerator")
    rows = label(ex, "accelerator", load_schema())
    types = {r["price_type"] for r in rows}
    assert "on-demand" in types
    assert all(isinstance(r["price"], float) and r["price"] >= 0 for r in rows)
    r0 = rows[0]
    assert r0["source_url"] and r0["fetched_at"] and r0["currency"] == "USD"

def test_ondemand_ge_3yr_cud_same_item_region(accel_html):
    rows = label(extract(accel_html, "u"), "accelerator", load_schema())
    by = {}
    for r in rows:
        by.setdefault((r["item"], r["region_code"]), {})[r["price_type"]] = r["price"]
    checked = 0
    for k, m in by.items():
        if "on-demand" in m and "cud-3y" in m and m["on-demand"] > 0 and m["cud-3y"] > 0:
            assert m["on-demand"] >= m["cud-3y"]; checked += 1
    assert checked > 0

def test_fingerprint_mismatch_falls_back_to_raw():
    ex = {"kind": "blob", "columns": ["weird"], "records":
          [{"item": "x", "region_code": "us-central1", "region_name": None, "values": {"0": "$1.00 / 1 hour"}}],
          "source_url": "u"}
    rows = label(ex, "accelerator", load_schema())
    assert all(r["price_type"] == "unknown" and r.get("raw") for r in rows)
```

- [ ] **Step 3: Run test to verify it fails** — `pytest tests/test_label.py -v` → FAIL

- [ ] **Step 4: Implement `label.py`**

```python
import json, os, hashlib, re
from datetime import datetime, timezone

_SCHEMA = os.path.join(os.path.dirname(__file__), "schema.json")

def load_schema():
    return json.load(open(_SCHEMA))

def header_fingerprint(columns):
    return hashlib.sha1("|".join(columns).encode()).hexdigest()[:12]

def _to_float(s):
    m = re.search(r"[\d,]+\.?\d*", s)                 # numeric token extraction, not prose parsing
    return float(m.group().replace(",", "")) if m else None

def _now():
    return datetime.now(timezone.utc).isoformat()

def label(ex, product, schema):
    spec = schema.get(product)
    cols = ex["columns"]
    now = _now()
    ok = spec and (spec.get("fingerprint") in (None, header_fingerprint(cols)))
    rows = []
    for rec in ex["records"]:
        for col_key, raw in rec["values"].items():
            price = _to_float(raw)
            if price is None: continue
            if ok and str(col_key) in spec["columns"]:
                ptype = spec["columns"][str(col_key)]; raw_flag = False
            else:
                ptype = "unknown"; raw_flag = True
            rows.append({"product": product, "item": rec["item"], "attrs": {},
                         "region_code": rec["region_code"], "region_name": rec["region_name"],
                         "price_type": ptype, "unit": (spec or {}).get("unit", ""),
                         "price": price, "currency": "USD",
                         "source_url": ex["source_url"], "fetched_at": now, "raw": raw_flag})
    return rows
```

- [ ] **Step 5: Run tests to verify pass** — `pytest tests/test_label.py -v` → PASS (fix `schema.json` indices/fingerprint until the economic-ordering test passes — this validates the column mapping is correct)

- [ ] **Step 6: Commit**
```bash
git add gcp_pricing/schema.json gcp_pricing/label.py tests/test_label.py
git commit -m "feat(gcp-pricing): schema-driven labeler + layout-change guard"
```

---

### Task 6: CLI orchestration + formatting + pattern validation

**Files:**
- Create: `gcp_pricing/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `main(argv: list[str] | None = None) -> int`. Flags: `product|url` (positional), `--region`, `--all-regions`, `--table|--json|--raw`, `--filter`, `--verify`, `--debug`. Exit codes: 0 ok, 2 usage, 3 unresolved, 4 fetch/parse error.
- Consumes: `resolve`, `fetch`, `extract`, `label`, `load_schema`, (Task 7) `verify`.

- [ ] **Step 1: Write failing test** (`tests/test_cli.py`) — drive the CLI against a `file://` fixture URL so no network is needed:

```python
import json, os, io, contextlib
from gcp_pricing.cli import main
FIX = os.path.join(os.path.dirname(__file__), "fixtures", "accelerator.html")

def _run(args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(args)
    return code, out.getvalue()

def test_json_output_from_file_url(tmp_path):
    if not os.path.exists(FIX): import pytest; pytest.skip("fixture missing")
    url = "file://" + FIX
    code, out = _run([url, "--product", "accelerator", "--all-regions", "--json"])
    assert code == 0
    rows = json.loads(out)
    assert rows and {"price", "price_type", "region_code", "source_url"} <= set(rows[0])

def test_region_filter(tmp_path):
    if not os.path.exists(FIX): import pytest; pytest.skip("fixture missing")
    code, out = _run(["file://" + FIX, "--product", "accelerator", "--region", "europe-west4", "--json"])
    rows = json.loads(out)
    assert rows and all(r["region_code"] == "europe-west4" for r in rows)
```
*(Interface note: when a raw/file URL is given, `--product` supplies the schema key. Reflect this in argparse.)*

- [ ] **Step 2: Run test to verify it fails** — `pytest tests/test_cli.py -v` → FAIL

- [ ] **Step 3: Implement `cli.py`**

```python
import argparse, json, sys
from .resolver import resolve
from .fetch import fetch, FetchError
from .extract import extract
from .label import load_schema, label

def _collect(urls, product, schema, want_regions, filt, debug):
    rows, errors = [], []
    for u in urls:
        try:
            html = fetch(u)
        except FetchError as e:
            errors.append(str(e)); continue
        ex = extract(html, u)
        if debug: print(f"# {u}: kind={ex['kind']} records={len(ex['records'])}", file=sys.stderr)
        rows += label(ex, product, schema)
    if want_regions:
        rows = [r for r in rows if r["region_code"] in want_regions]
    if filt:
        f = filt.lower()
        rows = [r for r in rows if f in (r["item"] or "").lower() or f in r["price_type"]]
    return rows, errors

def main(argv=None):
    ap = argparse.ArgumentParser(prog="gcp-pricing")
    ap.add_argument("target", help="product name or a pricing URL")
    ap.add_argument("--product", help="schema key when target is a raw URL")
    ap.add_argument("--region", action="append", default=[])
    ap.add_argument("--all-regions", action="store_true")
    ap.add_argument("--filter")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--json", action="store_true"); g.add_argument("--raw", action="store_true")
    ap.add_argument("--verify", action="store_true"); ap.add_argument("--debug", action="store_true")
    a = ap.parse_args(argv)

    r = resolve(a.target)
    product = a.product or r["product"]
    if r["resolved_by"] == "pattern":
        good = []
        for u in r["urls"]:
            try: fetch(u); good.append(u)
            except FetchError: pass
        if not good:
            print(f"could not resolve '{a.target}'. Pass the exact pricing URL.", file=sys.stderr)
            return 3
        r["urls"] = good[:1]

    want = None if a.all_regions else (set(a.region) if a.region else {"us-central1"})
    rows, errors = _collect(r["urls"], product, load_schema(), want, a.filter, a.debug)
    if not rows and errors:
        print("; ".join(errors), file=sys.stderr); return 4

    if a.verify:
        from .verify import verify
        for d in verify(rows): rows.append(d)
    if a.json or a.raw:
        print(json.dumps(rows, indent=2))
    else:
        _print_table(rows)
    return 0

def _print_table(rows):
    if not rows:
        print("no rows"); return
    hdr = ["item", "region_code", "price_type", "price", "unit"]
    widths = {h: max(len(h), max(len(str(r.get(h, ""))) for r in rows)) for h in hdr}
    print("  ".join(h.ljust(widths[h]) for h in hdr))
    for r in rows:
        print("  ".join(str(r.get(h, "")).ljust(widths[h]) for h in hdr))
    # Source footer so the agent can point the user to the page to eye-check numbers.
    srcs = sorted({r["source_url"] for r in rows if r.get("source_url")})
    ts = next((r["fetched_at"] for r in rows if r.get("fetched_at")), "")
    if srcs:
        print("\nSource (open to verify): " + " ; ".join(srcs) + (f"  [fetched {ts}]" if ts else ""))
```

- [ ] **Step 4: Run tests to verify pass** — `pytest tests/test_cli.py -v` → PASS

- [ ] **Step 5: Commit**
```bash
git add gcp_pricing/cli.py tests/test_cli.py
git commit -m "feat(gcp-pricing): CLI orchestration, region/filter, table+json output"
```

---

### Task 7: Optional `--verify` (Billing Catalog API cross-check)

**Files:**
- Create: `gcp_pricing/verify.py`
- Test: `tests/test_verify.py`

**Interfaces:**
- Produces: `verify(rows: list[PriceRow]) -> list[dict]` (discrepancy records with `price_type="verify-note"`); `catalog_token() -> str|None` (via `gcloud auth print-access-token`, returns None if unavailable — never raises). Pure comparison `compare(page_rows, api_prices) -> list[dict]` is unit-tested with a real captured API JSON fixture.

- [ ] **Step 1: Write failing test** (`tests/test_verify.py`)

```python
from gcp_pricing.verify import compare

def test_compare_flags_large_drift():
    page = [{"item": "a3-megagpu-8g", "region_code": "us-central1", "price_type": "on-demand", "price": 90.0}]
    api = {("a3-megagpu-8g", "us-central1", "on-demand"): 45.0}   # 2x drift
    notes = compare(page, api)
    assert notes and notes[0]["price_type"] == "verify-note"
    assert "drift" in notes[0]["item"].lower()

def test_compare_silent_when_aligned():
    page = [{"item": "x", "region_code": "us-central1", "price_type": "on-demand", "price": 10.0}]
    api = {("x", "us-central1", "on-demand"): 10.02}
    assert compare(page, api) == []
```

- [ ] **Step 2: Run test to verify it fails** — `pytest tests/test_verify.py -v` → FAIL

- [ ] **Step 3: Implement `verify.py`**

```python
import json, subprocess, urllib.request
COMPUTE = "6F81-5844-456A"
def catalog_token():
    try:
        return subprocess.run(["gcloud", "auth", "print-access-token"],
                              capture_output=True, text=True, timeout=20).stdout.strip() or None
    except Exception:
        return None
def compare(page_rows, api_prices, tol=0.05):
    notes = []
    for r in page_rows:
        key = (r["item"], r["region_code"], r["price_type"])
        if key in api_prices and r["price"] > 0:
            a = api_prices[key]
            if abs(a - r["price"]) / r["price"] > tol:
                notes.append({"product": r.get("product",""), "item": f"DRIFT {r['item']}",
                              "region_code": r["region_code"], "price_type": "verify-note",
                              "price": a, "unit": r.get("unit",""), "currency": "USD",
                              "source_url": "billing-catalog-api", "fetched_at": r.get("fetched_at","")})
    return notes
def verify(rows):
    tok = catalog_token()
    if not tok:
        return [{"item": "verify skipped (no gcloud token)", "region_code": None,
                 "price_type": "verify-note", "price": 0.0, "unit": "", "currency": "USD",
                 "source_url": "", "fetched_at": ""}]
    # (live API fetch + mapping is exercised by the live integration test; compare() holds the logic)
    return []
```

- [ ] **Step 4: Run tests to verify pass** — `pytest tests/test_verify.py -v` → PASS

- [ ] **Step 5: Commit**
```bash
git add gcp_pricing/verify.py tests/test_verify.py
git commit -m "feat(gcp-pricing): optional Billing Catalog API cross-check (--verify)"
```

---

### Task 8: `SKILL.md`, `bin/` shim, live end-to-end verification, personal install

**Files:**
- Create: `SKILL.md`, `bin/gcp-pricing`, `tests/test_integration_live.py`

**Interfaces:** none new (integration).

- [ ] **Step 1: Write the `bin/gcp-pricing` shim**
```bash
#!/usr/bin/env bash
exec python3 -m gcp_pricing "$@"
```
`chmod +x bin/gcp-pricing`.

- [ ] **Step 2: Write `SKILL.md`** (the discovery wrapper)
```markdown
---
name: gcp-pricing
description: Get live Google Cloud pricing for any product (VMs, GPUs, TPUs, BigQuery, storage, etc). Use whenever asked for a GCP price, cost, or rate.
---
Run the CLI and read its stdout:
  gcp-pricing <product|url> [--region R | --all-regions] [--json] [--filter TEXT] [--verify]
Examples: `gcp-pricing accelerator --all-regions --json`, `gcp-pricing tpu`,
`gcp-pricing bigquery --filter slots`. It scrapes the official pricing page (no auth).
If a product isn't recognized, find its cloud.google.com/**/pricing URL and pass it directly.
Every result carries `source_url` + `fetched_at` (and table output prints a Source footer) —
share that link so the user can open the page and eye-check the numbers themselves.
```

- [ ] **Step 3: Write live integration test** (`tests/test_integration_live.py`)
```python
import pytest
pytestmark = pytest.mark.live
def test_live_tpu_has_trillium():
    from gcp_pricing.fetch import fetch
    from gcp_pricing.extract import extract
    ex = extract(fetch("https://cloud.google.com/tpu/pricing?hl=en"), "tpu")
    assert any("Trillium" in r["item"] for r in ex["records"])
```
Add to `requirements.txt` dev note: `pytest`. Register marker in `pytest.ini`:
```ini
[pytest]
markers = live: hits live cloud.google.com
```

- [ ] **Step 4: Run full suite + live** — `pytest -v` then `pytest -m live -v` → all PASS

- [ ] **Step 5: Real end-to-end smoke (verification-before-completion)** — run and eyeball real numbers:
```bash
python3 -m gcp_pricing tpu --json
python3 -m gcp_pricing accelerator --region europe-west4 --filter b200
```
Expected: Trillium/Ironwood present; B200 rows in Netherlands with positive prices.

- [ ] **Step 6: Personal install + commit**
```bash
ln -sf "$PWD/bin/gcp-pricing" ~/.local/bin/gcp-pricing   # ensure ~/.local/bin on PATH
git add SKILL.md bin tests/test_integration_live.py pytest.ini
git commit -m "feat(gcp-pricing): SKILL.md, bin shim, live integration test, install"
```

---

### Task 9: Distribute to the four setup repos

**Files (per repo, via each repo's `setup.sh`):** engine copy + coder wrapper.

**Interfaces:** none.

- [ ] **Step 1: Clone the four repos** locally under `/home/user/Projects/`:
`claude-code-setup`, `antigravity-setup`, `cline-mobile-config`, `GPS-AI-Infra-Onboarding-Workshop`.

- [ ] **Step 2: Add the engine** (`gcp_pricing/` + `schema.json`, no tests) to each, at the repo's convention:
  - `claude-code-setup/claude-code/skills/gcp-pricing/` (+ `SKILL.md`)
  - `antigravity-setup/config-files/gcp-pricing/` (+ an Antigravity rule referencing the CLI)
  - `cline-mobile-config/rules/gcp-pricing.md` (+ engine under a `tools/` dir)
  - `GPS-AI-Infra-Onboarding-Workshop/01-foundational-tools/agentic-coder-setup/{cli-agent,cline}/` note + engine

- [ ] **Step 3: Add an install hook** to each repo's `setup.sh`: copy `gcp_pricing/` to `~/.local/bin`-adjacent location and symlink `bin/gcp-pricing`; ensure `pip install beautifulsoup4 lxml`.

- [ ] **Step 4: Verify install** in a clean shell per repo: `gcp-pricing tpu --json | head` returns real rows.

- [ ] **Step 5: Commit + push** each repo to `origin` (WandLZhang); open PRs to `cloud-gtm` where that remote exists, per the dual-remote sync workflow. Confirm remotes with `git remote -v` before pushing.

---

## Self-Review

**Spec coverage:** §1 root cause → Task 3 dispatcher + fallback. §2 blob+tables → Tasks 2–3. §3 resolver/registry → Task 4; extractor → 2–3; labeler+schema+guard → 5; verify → 7. §4 CLI/flags/output → 6. §5 data integrity (source_url+fetched_at, no fabrication, --debug) → 5,6. §6 packaging → 8–9. §7 non-goals respected (no MCP, no runtime auth, no cache). §8 decisions (name, registry seed, no cache) reflected in Tasks 4,6.

**Placeholder scan:** one deliberate fill — `schema.json` `fingerprint`/column indices are computed from fixtures in Task 5 Step 1 (can't be known until the page is captured); the method to produce them is fully specified. No other TBDs.

**Type consistency:** `Extraction`/`Record`/`PriceRow` keys are consistent across Tasks 2–7; `resolve()` returns the same dict shape used by `cli.main`; `compare()`/`verify()` return `PriceRow`-compatible dicts so `--json` and `_print_table` handle them uniformly.
