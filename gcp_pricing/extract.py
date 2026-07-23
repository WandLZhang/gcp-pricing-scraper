"""Extract raw pricing data from a GCP pricing page — verbatim, no interpretation.

Philosophy: the page structure is dynamic and product-specific. Any attempt to map
columns to canonical price types, align cells, or normalize values is brittle and WILL
break when Google changes the layout. So we do none of that. We return the page's own
column headers and the raw cell strings, aligned only in the order the page presents them,
and let the consuming agent read the table itself.

Two sources, both browserless:
- The inline JSON blob (compute families, BigQuery, Cloud Run): holds every region.
- Visible <table>s (TPU, storage, Spanner, ...): dumped verbatim.
"""
import json
from bs4 import BeautifulSoup

_HINT = ("us-", "europe-", "asia-", "africa-", "me-", "australia-",
         "northamerica-", "southamerica-")
_PLACEHOLDERS = ("n/a", "not available", "-", "—", "–", "")


def _is_region_label(s):
    return isinstance(s, str) and s.endswith(")") and "(" in s and any(h in s for h in _HINT)


def _strings(node, out):
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, list):
        for e in node:
            _strings(e, out)


def _all_strings(node):
    out = []
    _strings(node, out)
    return out


def _strip_tags(s):
    # remove HTML tags only (the blob wraps cells in <p>...); not price parsing
    return BeautifulSoup(s, "lxml").get_text(" ", strip=True) if "<" in s else s.strip()


def _has_price(node):
    return any(x.strip().startswith("$") for x in _all_strings(node))


def _count_prices(node):
    return sum(1 for x in _all_strings(node) if x.strip().startswith("$"))


# ---------------------------------------------------------------- visible tables

def table_sheets(html):
    """Every visible <table> that contains a price, dumped verbatim as {headers, rows}."""
    soup = BeautifulSoup(html, "lxml")
    sheets = []
    for tbl in soup.find_all("table"):
        trs = tbl.find_all("tr")
        if not trs:
            continue
        headers = [c.get_text(" ", strip=True) for c in trs[0].find_all(["th", "td"])]
        rows = []
        for tr in trs[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)
        if rows and any("$" in c for row in rows for c in row):
            sheets.append({"headers": headers, "rows": rows})
    return sheets


def _widest_headers(html):
    """The widest visible header row (the compute machine table) — used to label blob rows,
    which the page lays out in the same column order."""
    best = []
    for s in table_sheets(html):
        if len(s["headers"]) > len(best):
            best = s["headers"]
    return best


# ---------------------------------------------------------------- inline blob

def find_blob(html):
    """Return the decoded inline JSON pricing array, or None."""
    soup = BeautifulSoup(html, "lxml")
    best = None
    for sc in soup.find_all("script"):
        t = sc.string or sc.get_text() or ""
        if "[[" in t and sum(t.count(h) for h in _HINT) > 20:
            try:
                data, _ = json.JSONDecoder().raw_decode(t, t.find("[["))
            except Exception:
                continue
            n = sum(1 for s in _all_strings(data) if _is_region_label(s))
            if best is None or n > best[0]:
                best = (n, data)
    return best[1] if best else None


def _lists(node):
    if isinstance(node, list):
        yield node
        for e in node:
            yield from _lists(e)


def _cell_text(cell):
    for s in _all_strings(cell):
        txt = _strip_tags(s)
        if txt:
            return txt
    return ""


def _region_of(node):
    for s in _all_strings(node):
        if _is_region_label(s):
            return s
    return None


def _rows_list(block):
    best = None
    for lst in _lists(block):
        pc = sum(1 for c in lst if isinstance(c, list) and _has_price(c))
        if pc >= 2 and (best is None or pc > best[0]):
            best = (pc, lst)
    return best[1] if best else None


def _cells_list(row):
    best = None
    for lst in _lists(row):
        cnt = sum(1 for c in lst if isinstance(c, list) and _cell_text(c))
        if cnt and (best is None or cnt > best[0]):
            best = (cnt, lst)
    return best[1] if best else None


def _row_cells(row):
    cl = _cells_list(row)
    return [_cell_text(c) for c in cl if isinstance(c, list)] if cl else []


def _blocks_list(data):
    """The list whose children are per-region blocks (each: a region label + several prices)."""
    best = None
    for lst in _lists(data):
        cnt = sum(1 for c in lst if isinstance(c, list) and _region_of(c) and _count_prices(c) >= 4)
        if cnt >= 2 and (best is None or cnt > best[0]):
            best = (cnt, lst)
    return best[1] if best else None


def walk_blob(data):
    """Raw per-region rows: [(region_label, [cell, cell, ...]), ...], cells verbatim.

    One row per (region, item), keeping the widest hourly row — the page fragments a single
    logical row across sub-blocks (and a monthly mirror). This is reassembly of the page's
    own row, not interpretation: cells are never relabeled, reordered, or normalized.
    """
    blocks = _blocks_list(data)
    if blocks is None:
        return []
    by = {}
    for block in blocks:
        region = _region_of(block)
        if not region:
            continue
        rl = _rows_list(block)
        if rl is None:
            continue
        for r in rl:
            if not isinstance(r, list):
                continue
            cells = _row_cells(r)
            price_cells = [c for c in cells if c.startswith("$")]
            if not price_cells:
                continue
            item = next((c for c in cells if c and not c.startswith("$")
                         and c.strip().lower() not in _PLACEHOLDERS), "")
            if not item:
                continue
            monthly = any("month" in c for c in price_cells)
            score = (0 if monthly else 1, len(price_cells))   # prefer hourly, then widest
            key = (region, item)
            if key not in by or score > by[key][0]:
                by[key] = (score, cells)
    return [(region, cells) for (region, _item), (_score, cells) in
            ((k, v) for k, v in by.items())]


# ---------------------------------------------------------------- dispatch

def extract(html, url):
    """Return {source_url, sheets:[{headers, rows}]} — raw, verbatim.

    Compute/BigQuery/Cloud Run pages -> one sheet from the all-region blob, labeled with the
    page's own header row (blob columns follow the same order). Everything else -> the visible
    tables dumped as-is. No canonicalization anywhere.
    """
    data = find_blob(html)
    if data is not None:
        rows = walk_blob(data)
        good = [c for _r, c in rows if c and c[0] and not c[0].startswith("$")]
        headers = _widest_headers(html)
        if good and headers:
            sheet = {"headers": ["Region"] + headers,
                     "rows": [[region] + cells for region, cells in rows]}
            return {"source_url": url, "sheets": [sheet]}
    return {"source_url": url, "sheets": table_sheets(html)}
