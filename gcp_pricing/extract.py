"""Capture a GCP pricing page. Do not select, do not interpret.

The old version tried to find "the pricing table" and threw the rest away: it kept a
<table> only if it contained a "$", it never read prose, and it walked the inline JSON
guessing which nested list was the real one. That silently lost minimum storage durations,
free-tier limits, worked examples that define billing units, and 13 of 14 machine families.

So this module does the least possible:

  text     the whole page as readable markdown - every heading, paragraph, list item and
           table, in document order, no filtering. Copy-paste parity.
  regions  rows recovered from the inline JSON blob, which is the only place the page keeps
           its non-default regions. Every region-bearing row is emitted; near-duplicates are
           left in. The reader dedupes, not the tool.

Both are raw. Deciding what matters is the caller's job.
"""
import json
import re
from bs4 import BeautifulSoup, NavigableString

_HINT = ("us-", "europe-", "asia-", "africa-", "me-", "australia-",
         "northamerica-", "southamerica-")

# Chrome that appears on every cloud.google.com page and carries no pricing signal.
_SKIP_TAGS = ("script", "style", "noscript", "nav", "footer", "svg", "form", "iframe")
_BLOCK = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "blockquote", "dt", "dd")


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
    return BeautifulSoup(s, "lxml").get_text(" ", strip=True) if "<" in s else s.strip()


# ---------------------------------------------------------------- visible page -> markdown

def _table_md(tbl):
    """A <table> as a markdown table. Every table, priced or not."""
    trs = tbl.find_all("tr")
    if not trs:
        return None
    rows = []
    for tr in trs:
        cells = [c.get_text(" ", strip=True).replace("|", "\\|").replace("\xa0", " ")
                 for c in tr.find_all(["td", "th"])]
        if cells:
            rows.append(cells)
    if not rows:
        return None
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    head, body = rows[0], rows[1:]
    out = ["| " + " | ".join(head) + " |",
           "|" + "---|" * width]
    for r in body:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def page_text(html):
    """The whole readable page, in document order: headings, prose, lists, and ALL tables.

    No price gate. Minimum-duration tables, eligibility lists, free-tier limits and the
    worked examples that define billing units have no "$" in them and were the exact things
    the previous implementation discarded.
    """
    soup = BeautifulSoup(html, "lxml")
    for t in soup.find_all(_SKIP_TAGS):
        t.decompose()

    parts, seen = [], set()

    def emit(s):
        s = re.sub(r"[ \t\xa0]+", " ", s).strip()
        if not s or s in seen:
            return
        seen.add(s)
        parts.append(s)

    for el in soup.find_all(_BLOCK + ("table",)):
        # a block nested inside a table is rendered by the table itself
        if el.name != "table" and el.find_parent("table"):
            continue
        if el.name == "table":
            md = _table_md(el)
            if md:
                parts.append(md)      # tables bypass dedupe: identical shapes are common
            continue
        txt = el.get_text(" ", strip=True)
        if not txt:
            continue
        if el.name.startswith("h") and len(el.name) == 2 and el.name[1].isdigit():
            emit("#" * int(el.name[1]) + " " + txt)
        elif el.name == "li":
            emit("- " + txt)
        else:
            emit(txt)

    return "\n\n".join(parts)


def table_sheets(html):
    """Every visible <table>, as {headers, rows}. No price filter."""
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
        if rows:
            sheets.append({"headers": headers, "rows": rows,
                           "priced": any("$" in c for row in rows for c in row)})
    return sheets


# ---------------------------------------------------------------- inline blob

def find_blob(html):
    """The decoded inline JSON pricing array (holds every region), or None."""
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


def walk_blob(data):
    """Every region-bearing row in the blob: [(region, [cell, ...]), ...].

    Shape-agnostic on purpose. A "row" is any list whose descendants include exactly one
    region label and at least one non-empty leaf; its cells are those leaves in document
    order. No scoring, no picking a best block, no dedupe - all three of those are how the
    previous version lost 13 of 14 machine families.
    """
    if data is None:
        return []
    out = []
    for lst in _lists(data):
        regions = [s for s in _all_strings(lst) if _is_region_label(s)]
        if len(regions) != 1:
            continue
        # innermost list carrying exactly one region: its non-region leaves are the cells
        if any(len([s for s in _all_strings(c) if _is_region_label(s)]) == 1
               for c in lst if isinstance(c, list)):
            continue                       # an ancestor of the real row; skip
        cells = []
        for s in _all_strings(lst):
            if _is_region_label(s):
                continue
            txt = _strip_tags(s)
            if txt:
                cells.append(txt)
        if cells:
            out.append((regions[0], cells))
    return out


# ---------------------------------------------------------------- dispatch

def extract(html, url):
    """{source_url, text, regions, tables} - captured, not curated."""
    tables = table_sheets(html)
    text = page_text(html)
    regions = walk_blob(find_blob(html))
    return {
        "source_url": url,
        "text": text,
        "regions": [{"region": r, "cells": c} for r, c in regions],
        "tables": tables,
        "coverage": {
            "tables": len(tables),
            "tables_priced": sum(1 for t in tables if t["priced"]),
            "region_rows": len(regions),
            "text_chars": len(text),
        },
    }
