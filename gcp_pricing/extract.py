"""Extract structured pricing from a GCP pricing page.

Two mechanisms, both browserless and regex-free for the actual price data:
- Embedded JSON blob (compute families, BigQuery): all-region data serialized inline.
- Visible <table>s (TPU, storage, Lustre, ...): regions usually appear as rows.

Navigation of the blob is *structural* (locate nodes by content), never by absolute
index, because the page's widget index drifts between fetches.
"""
import json
import re
from bs4 import BeautifulSoup

_HINT = ("us-", "europe-", "asia-", "africa-", "me-", "australia-",
         "northamerica-", "southamerica-")


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
    return re.sub(r"<[^>]+>", "", s).strip()   # HTML tag removal only, not price parsing


def _has_price(node):
    return any(x.strip().startswith("$") for x in _all_strings(node))


def _count_prices(node):
    return sum(1 for x in _all_strings(node) if x.strip().startswith("$"))


# ---------------------------------------------------------------- blob path

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
    """The child list inside a block that holds the machine rows (max #price-bearing children)."""
    best = None
    for lst in _lists(block):
        pc = sum(1 for c in lst if isinstance(c, list) and _has_price(c))
        if pc >= 2 and (best is None or pc > best[0]):
            best = (pc, lst)
    return best[1] if best else None


def _cells_list(row):
    """The descendant list whose children are the row's cells (max cell count)."""
    best = None
    for lst in _lists(row):
        cnt = sum(1 for c in lst if isinstance(c, list) and _cell_text(c))
        if cnt and (best is None or cnt > best[0]):
            best = (cnt, lst)
    return best[1] if best else None


def _row_cells(row):
    cl = _cells_list(row)
    if cl is None:
        return []
    return [_cell_text(c) for c in cl if isinstance(c, list)]


_HEADER_WORDS = ("On-Demand", "Spot", "CUD", "Flex", "USD", "commitment", "Price", "price")


def _looks_header(cells):
    return any(any(w in c for w in _HEADER_WORDS) for c in cells)


def _blocks_list(data):
    """The list whose children are per-region blocks (each has a region label + prices)."""
    best = None
    for lst in _lists(data):
        # a real per-region block has a region label AND several prices (>=4);
        # this rejects decoy lists (e.g. region dropdown with one "starting at" price each)
        cnt = sum(1 for c in lst if isinstance(c, list) and _region_of(c) and _count_prices(c) >= 4)
        if cnt >= 2 and (best is None or cnt > best[0]):
            best = (cnt, lst)
    return best[1] if best else None


def walk_blob(data):
    """Return (regions, columns, records). Each record carries its own region + unit.

    Price columns are keyed by ordinal ('0','1',...); the visible table supplies the
    human names by the same left-to-right ordering (see extract()). Records are deduped
    per (item, region, unit), keeping the widest row — the page splits one region across
    several blocks (e.g. a 4-column and a 6-column hourly variant).
    """
    blocks = _blocks_list(data)
    if blocks is None:
        return [], [], []
    regions, by, width = {}, {}, 0
    for block in blocks:
        region = _region_of(block)
        if not region:
            continue
        code = region[region.rfind("(") + 1:-1]
        regions[code] = region
        rl = _rows_list(block)
        if rl is None:
            continue
        for r in rl:
            if not isinstance(r, list):
                continue
            cells = _row_cells(r)
            pr_idx = [i for i, x in enumerate(cells) if x.startswith("$")]
            if not pr_idx:
                continue
            item = next((x for x in cells if x and not x.startswith("$")), "")
            if not item:
                continue
            unit = "month" if any("month" in cells[i] for i in pr_idx) else "hour"
            values = {str(k): cells[i] for k, i in enumerate(pr_idx)}
            width = max(width, len(values))
            key = (item, code, unit)
            if key not in by or len(values) > len(by[key]["values"]):
                by[key] = {"item": item, "region_code": code, "region_name": region,
                           "unit": unit, "values": values}
    columns = [str(k) for k in range(width)]
    return ([{"code": c, "name": n} for c, n in regions.items()], columns, list(by.values()))


# ---------------------------------------------------------------- table path

def _looks_like_code(s):
    return isinstance(s, str) and any(s.startswith(h) for h in _HINT) and " " not in s


def extract_tables(html):
    """Extract visible <table>s (TPU/storage/Lustre etc.), regions usually as rows."""
    soup = BeautifulSoup(html, "lxml")
    columns, records = [], []
    for tbl in soup.find_all("table"):
        trs = tbl.find_all("tr")
        if not trs:
            continue
        header = [c.get_text(" ", strip=True) for c in trs[0].find_all(["th", "td"])]
        for tr in trs[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if not cells:
                continue
            values = {(header[i] if i < len(header) else str(i)): cells[i] for i in range(len(cells))}
            rc = next((c for c in cells if _looks_like_code(c)), None)
            records.append({"item": cells[0], "region_code": rc, "region_name": None,
                            "unit": "", "values": values})
        if len(header) > len(columns):
            columns = header
    return columns, records


def extract(html, url):
    """Dispatch: prefer the all-region blob; fall back to visible tables."""
    data = find_blob(html)
    if data is not None:
        regions, columns, records = walk_blob(data)
        if records:
            return {"kind": "blob", "columns": columns, "records": records, "source_url": url}
    columns, records = extract_tables(html)
    return {"kind": "tables", "columns": columns, "records": records, "source_url": url}
